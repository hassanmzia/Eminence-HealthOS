"""
Eminence HealthOS — Platform Hardening Tests (Sprint 25-26)
Tests for security middleware, HIPAA validation, tenant isolation,
input sanitization, and production readiness.
"""

from __future__ import annotations

import uuid

import pytest

from healthos_platform.agents.types import AgentInput, AgentStatus


# ── Helpers ──────────────────────────────────────────────────────────────────

def _input(context: dict) -> AgentInput:
    return AgentInput(
        org_id=uuid.uuid4(),
        trigger="test",
        context=context,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# INPUT SANITIZER
# ═══════════════════════════════════════════════════════════════════════════════


class TestInputSanitizer:

    def test_detect_sql_injection(self):
        from healthos_platform.security.input_sanitizer import InputSanitizer

        assert InputSanitizer.detect_sql_injection("SELECT * FROM users")
        assert InputSanitizer.detect_sql_injection("1; DROP TABLE patients")
        assert InputSanitizer.detect_sql_injection("' OR 1=1")
        assert not InputSanitizer.detect_sql_injection("John Smith")
        assert not InputSanitizer.detect_sql_injection("patient-123")

    def test_detect_xss(self):
        from healthos_platform.security.input_sanitizer import InputSanitizer

        assert InputSanitizer.detect_xss("<script>alert('xss')</script>")
        assert InputSanitizer.detect_xss("javascript:void(0)")
        assert InputSanitizer.detect_xss('<img onerror="alert(1)">')
        assert not InputSanitizer.detect_xss("Normal text content")

    def test_detect_path_traversal(self):
        from healthos_platform.security.input_sanitizer import InputSanitizer

        assert InputSanitizer.detect_path_traversal("../../etc/passwd")
        assert InputSanitizer.detect_path_traversal("..\\windows\\system32")
        assert not InputSanitizer.detect_path_traversal("/api/v1/patients")

    def test_sanitize_string(self):
        from healthos_platform.security.input_sanitizer import InputSanitizer

        result = InputSanitizer.sanitize_string("<script>alert('xss')</script>")
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_validate_input_clean(self):
        from healthos_platform.security.input_sanitizer import InputSanitizer

        threats = InputSanitizer.validate_input({
            "name": "John Smith",
            "age": 45,
            "conditions": ["diabetes", "hypertension"],
        })
        assert len(threats) == 0

    def test_validate_input_threats(self):
        from healthos_platform.security.input_sanitizer import InputSanitizer

        threats = InputSanitizer.validate_input({
            "name": "'; DROP TABLE patients;--",
            "note": "<script>steal_phi()</script>",
        })
        assert len(threats) >= 2

    def test_validate_nested_depth(self):
        from healthos_platform.security.input_sanitizer import InputSanitizer

        # Build deeply nested structure
        data: dict = {"level": "deep"}
        for _ in range(15):
            data = {"nested": data}

        threats = InputSanitizer.validate_input(data)
        assert any("nesting depth" in t for t in threats)

    def test_sanitize_dict(self):
        from healthos_platform.security.input_sanitizer import InputSanitizer

        result = InputSanitizer.sanitize_dict({
            "name": "<b>bold</b>",
            "nested": {"value": "<script>x</script>"},
            "count": 42,
        })
        assert "&lt;b&gt;" in result["name"]
        assert "&lt;script&gt;" in result["nested"]["value"]
        assert result["count"] == 42


# ═══════════════════════════════════════════════════════════════════════════════
# RATE LIMITER
# ═══════════════════════════════════════════════════════════════════════════════


class TestRateLimiter:

    def test_token_bucket_allows_within_capacity(self):
        from healthos_platform.security.rate_limiter import TokenBucket

        bucket = TokenBucket(capacity=10, refill_rate=1.0)
        for _ in range(10):
            assert bucket.consume()

    def test_token_bucket_blocks_over_capacity(self):
        from healthos_platform.security.rate_limiter import TokenBucket

        bucket = TokenBucket(capacity=5, refill_rate=0.0)
        for _ in range(5):
            bucket.consume()
        assert not bucket.consume()

    def test_token_bucket_refills(self):
        import time
        from healthos_platform.security.rate_limiter import TokenBucket

        bucket = TokenBucket(capacity=2, refill_rate=100.0)  # Fast refill
        bucket.consume()
        bucket.consume()
        time.sleep(0.05)  # Allow refill
        assert bucket.consume()

    def test_retry_after(self):
        from healthos_platform.security.rate_limiter import TokenBucket

        bucket = TokenBucket(capacity=1, refill_rate=1.0)
        bucket.consume()
        assert bucket.retry_after >= 0


# ═══════════════════════════════════════════════════════════════════════════════
# SECURITY HEADERS
# ═══════════════════════════════════════════════════════════════════════════════


class TestSecurityHeaders:

    def test_security_headers_defined(self):
        from healthos_platform.security.headers import SECURITY_HEADERS

        assert "X-Content-Type-Options" in SECURITY_HEADERS
        assert "X-Frame-Options" in SECURITY_HEADERS
        assert "Strict-Transport-Security" in SECURITY_HEADERS
        assert "Content-Security-Policy" in SECURITY_HEADERS
        assert "Referrer-Policy" in SECURITY_HEADERS
        assert "Cache-Control" in SECURITY_HEADERS

    def test_xframe_deny(self):
        from healthos_platform.security.headers import SECURITY_HEADERS
        assert SECURITY_HEADERS["X-Frame-Options"] == "DENY"

    def test_hsts_includes_subdomains(self):
        from healthos_platform.security.headers import SECURITY_HEADERS
        assert "includeSubDomains" in SECURITY_HEADERS["Strict-Transport-Security"]

    def test_csp_no_unsafe_eval(self):
        from healthos_platform.security.headers import SECURITY_HEADERS
        assert "unsafe-eval" not in SECURITY_HEADERS["Content-Security-Policy"]

    def test_cache_no_store(self):
        from healthos_platform.security.headers import SECURITY_HEADERS
        assert "no-store" in SECURITY_HEADERS["Cache-Control"]


# ═══════════════════════════════════════════════════════════════════════════════
# TENANT ISOLATION
# ═══════════════════════════════════════════════════════════════════════════════


class TestTenantIsolation:

    def test_tenant_scope_creation(self):
        from healthos_platform.security.tenant_isolation import TenantScope

        scope = TenantScope(
            tenant_id="t-001",
            org_id=uuid.uuid4(),
            user_id="u-001",
            role="clinician",
            permissions=frozenset(["patient:read", "vitals:read"]),
        )
        assert scope.tenant_id == "t-001"
        assert scope.has_permission("patient:read")
        assert not scope.has_permission("admin:all")

    def test_tenant_scope_immutable(self):
        from healthos_platform.security.tenant_isolation import TenantScope

        scope = TenantScope(
            tenant_id="t-001",
            org_id=uuid.uuid4(),
            user_id="u-001",
            role="admin",
            permissions=frozenset(["admin:all"]),
        )
        with pytest.raises(AttributeError):
            scope.tenant_id = "t-002"  # type: ignore

    def test_cross_tenant_access_blocked(self):
        from healthos_platform.security.tenant_isolation import TenantScope

        scope = TenantScope(
            tenant_id="t-001",
            org_id=uuid.uuid4(),
            user_id="u-001",
            role="clinician",
            permissions=frozenset(),
        )
        assert scope.can_access_tenant("t-001")
        assert not scope.can_access_tenant("t-002")

    def test_system_role_cross_tenant(self):
        from healthos_platform.security.tenant_isolation import TenantScope

        scope = TenantScope(
            tenant_id="system",
            org_id=uuid.uuid4(),
            user_id="system",
            role="system",
            permissions=frozenset(["admin:all"]),
        )
        assert scope.can_access_tenant("t-001")
        assert scope.can_access_tenant("t-002")

    def test_context_var_set_get(self):
        from healthos_platform.security.tenant_isolation import (
            TenantScope,
            set_tenant_scope,
            get_tenant_scope,
        )

        scope = TenantScope(
            tenant_id="t-test",
            org_id=uuid.uuid4(),
            user_id="u-test",
            role="admin",
            permissions=frozenset(["admin:all"]),
        )
        set_tenant_scope(scope)
        retrieved = get_tenant_scope()
        assert retrieved is not None
        assert retrieved.tenant_id == "t-test"

    def test_require_tenant_scope_raises(self):
        from healthos_platform.security.tenant_isolation import (
            TenantIsolationError,
            require_tenant_scope,
            _current_tenant,
        )

        _current_tenant.set(None)
        with pytest.raises(TenantIsolationError):
            require_tenant_scope()

    def test_tenant_query_filter_raises_without_context(self):
        from healthos_platform.security.tenant_isolation import (
            TenantIsolationError,
            TenantQueryFilter,
            _current_tenant,
        )

        _current_tenant.set(None)
        with pytest.raises(TenantIsolationError):
            TenantQueryFilter.apply_filter(None)


# ═══════════════════════════════════════════════════════════════════════════════
# HIPAA COMPLIANCE AGENT
# ═══════════════════════════════════════════════════════════════════════════════


class TestHIPAAComplianceAgent:

    @pytest.fixture
    def agent(self):
        from healthos_platform.security.hipaa_validator import HIPAAComplianceAgent
        return HIPAAComplianceAgent()

    @pytest.mark.asyncio
    async def test_full_audit(self, agent):
        output = await agent.run(_input({"action": "full_audit"}))
        assert output.status == AgentStatus.COMPLETED
        r = output.result
        assert "summary" in r
        assert r["summary"]["total_checks"] > 0
        assert r["summary"]["compliance_pct"] > 0
        assert "by_category" in r
        assert "administrative" in r["by_category"]
        assert "technical" in r["by_category"]

    @pytest.mark.asyncio
    async def test_technical_check(self, agent):
        output = await agent.run(_input({"action": "technical_check"}))
        assert output.status == AgentStatus.COMPLETED
        assert output.result["total"] > 0
        assert output.result["passed"] > 0

    @pytest.mark.asyncio
    async def test_phi_scan_clean(self, agent):
        output = await agent.run(_input({
            "action": "phi_scan",
            "text": "This is a normal clinical note without PHI.",
        }))
        assert output.status == AgentStatus.COMPLETED
        assert output.result["has_phi"] is False
        assert output.result["detection_count"] == 0

    @pytest.mark.asyncio
    async def test_phi_scan_with_phi(self, agent):
        output = await agent.run(_input({
            "action": "phi_scan",
            "text": "Patient SSN is 123-45-6789 and phone is (555) 123-4567.",
        }))
        assert output.status == AgentStatus.COMPLETED
        assert output.result["has_phi"] is True
        assert output.result["detection_count"] > 0

    @pytest.mark.asyncio
    async def test_compliance_score(self, agent):
        output = await agent.run(_input({"action": "compliance_score"}))
        assert output.status == AgentStatus.COMPLETED
        assert output.result["overall_score"] > 0
        assert output.result["risk_level"] in ("low", "moderate", "high", "critical")
        assert len(output.result["top_risks"]) == 3

    @pytest.mark.asyncio
    async def test_unknown_action(self, agent):
        output = await agent.run(_input({"action": "invalid"}))
        assert output.status == AgentStatus.WAITING_HITL


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTING TABLE — HIPAA COMPLIANCE
# ═══════════════════════════════════════════════════════════════════════════════


class TestHardeningRouting:

    def test_rate_limit_tiers_defined(self):
        from healthos_platform.security.rate_limiter import RATE_LIMITS

        assert "default" in RATE_LIMITS
        assert "auth" in RATE_LIMITS
        assert RATE_LIMITS["auth"]["capacity"] < RATE_LIMITS["default"]["capacity"]

    def test_hipaa_checks_cover_all_categories(self):
        from healthos_platform.security.hipaa_validator import HIPAA_CHECKS

        assert "administrative" in HIPAA_CHECKS
        assert "physical" in HIPAA_CHECKS
        assert "technical" in HIPAA_CHECKS
        assert len(HIPAA_CHECKS["technical"]) >= 6
