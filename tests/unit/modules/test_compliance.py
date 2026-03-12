"""Tests for the Compliance & Governance module agents."""

import uuid
import pytest

from healthos_platform.agents.types import AgentInput, AgentStatus

DEFAULT_ORG = uuid.UUID("00000000-0000-0000-0000-000000000001")
PATIENT_ID = uuid.UUID("00000000-0000-0000-0000-000000000099")


def _input(action: str, **extra) -> AgentInput:
    return AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=PATIENT_ID,
        trigger=f"compliance.{action}",
        context={"action": action, **extra},
    )


# ── HIPAA Compliance Monitor Agent ──────────────────────────────────

class TestHIPAAComplianceMonitorAgent:
    @pytest.fixture
    def agent(self):
        from modules.compliance.agents.hipaa_compliance_monitor import HIPAAComplianceMonitorAgent
        return HIPAAComplianceMonitorAgent()

    @pytest.mark.asyncio
    async def test_full_scan(self, agent):
        out = await agent.run(_input("full_scan"))
        assert out.status == AgentStatus.COMPLETED
        assert "overall_score" in out.result
        assert "safeguards" in out.result

    @pytest.mark.asyncio
    async def test_access_audit(self, agent):
        out = await agent.run(_input("access_audit", time_range="7d"))
        assert out.status == AgentStatus.COMPLETED
        assert "findings" in out.result

    @pytest.mark.asyncio
    async def test_phi_exposure_check(self, agent):
        out = await agent.run(_input("phi_exposure_check",
                                      data_sources=["logs", "api_responses"]))
        assert out.status == AgentStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_breach_detection(self, agent):
        out = await agent.run(_input("breach_detection"))
        assert out.status == AgentStatus.COMPLETED
        assert "severity" in out.result

    @pytest.mark.asyncio
    async def test_unknown_action(self, agent):
        out = await agent.run(_input("nonexistent"))
        assert out.status == AgentStatus.FAILED


# ── AI Governance Agent ─────────────────────────────────────────────

class TestAIGovernanceAgent:
    @pytest.fixture
    def agent(self):
        from modules.compliance.agents.ai_governance import AIGovernanceAgent
        return AIGovernanceAgent()

    @pytest.mark.asyncio
    async def test_model_inventory(self, agent):
        out = await agent.run(_input("model_inventory"))
        assert out.status == AgentStatus.COMPLETED
        assert "models" in out.result
        assert len(out.result["models"]) > 0

    @pytest.mark.asyncio
    async def test_drift_detection(self, agent):
        out = await agent.run(_input("drift_detection", model_name="risk_scoring"))
        assert out.status == AgentStatus.COMPLETED
        assert "psi" in out.result

    @pytest.mark.asyncio
    async def test_bias_audit(self, agent):
        out = await agent.run(_input("bias_audit", model_name="risk_scoring"))
        assert out.status == AgentStatus.COMPLETED
        assert "demographic_analysis" in out.result

    @pytest.mark.asyncio
    async def test_performance_report(self, agent):
        out = await agent.run(_input("performance_report"))
        assert out.status == AgentStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_governance_check(self, agent):
        out = await agent.run(_input("governance_check"))
        assert out.status == AgentStatus.COMPLETED


# ── Consent Management Agent ────────────────────────────────────────

class TestConsentManagementAgent:
    @pytest.fixture
    def agent(self):
        from modules.compliance.agents.consent_management import ConsentManagementAgent
        return ConsentManagementAgent()

    @pytest.mark.asyncio
    async def test_check_consent(self, agent):
        inp = _input("check_consent", purpose="treatment")
        out = await agent.run(inp)
        assert out.status == AgentStatus.COMPLETED
        assert "allowed" in out.result

    @pytest.mark.asyncio
    async def test_record_consent(self, agent):
        inp = _input("record_consent", purpose="research",
                      scope="clinical_trials", duration_days=365)
        out = await agent.run(inp)
        assert out.status == AgentStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_revoke_consent(self, agent):
        inp = _input("revoke_consent", purpose="data_sharing")
        out = await agent.run(inp)
        assert out.status == AgentStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_consent_summary(self, agent):
        out = await agent.run(_input("consent_summary"))
        assert out.status == AgentStatus.COMPLETED
        assert "consents" in out.result

    @pytest.mark.asyncio
    async def test_consent_audit(self, agent):
        out = await agent.run(_input("consent_audit"))
        assert out.status == AgentStatus.COMPLETED


# ── Regulatory Reporting Agent ──────────────────────────────────────

class TestRegulatoryReportingAgent:
    @pytest.fixture
    def agent(self):
        from modules.compliance.agents.regulatory_reporting import RegulatoryReportingAgent
        return RegulatoryReportingAgent()

    @pytest.mark.asyncio
    async def test_generate_report(self, agent):
        inp = _input("generate_report", framework="HIPAA")
        out = await agent.run(inp)
        assert out.status == AgentStatus.COMPLETED
        assert "report" in out.result

    @pytest.mark.asyncio
    async def test_compliance_dashboard(self, agent):
        out = await agent.run(_input("compliance_dashboard"))
        assert out.status == AgentStatus.COMPLETED
        assert "frameworks" in out.result

    @pytest.mark.asyncio
    async def test_gap_analysis(self, agent):
        inp = _input("gap_analysis", framework="SOC2")
        out = await agent.run(inp)
        assert out.status == AgentStatus.COMPLETED
        assert "gaps" in out.result

    @pytest.mark.asyncio
    async def test_audit_package(self, agent):
        out = await agent.run(_input("audit_package", framework="HIPAA"))
        assert out.status == AgentStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_regulatory_calendar(self, agent):
        out = await agent.run(_input("regulatory_calendar"))
        assert out.status == AgentStatus.COMPLETED
        assert "deadlines" in out.result


# ── Registration & Routing ──────────────────────────────────────────

class TestComplianceRegistration:
    def test_register_agents(self):
        from modules.compliance.agents import register_compliance_agents
        register_compliance_agents()
        from healthos_platform.orchestrator.registry import registry
        assert registry.get("hipaa_compliance_monitor") is not None
        assert registry.get("ai_governance") is not None
        assert registry.get("consent_management") is not None
        assert registry.get("regulatory_reporting") is not None

    def test_routing_entries(self):
        from healthos_platform.orchestrator.router import ROUTING_TABLE
        assert "compliance.hipaa.scan" in ROUTING_TABLE
        assert "compliance.governance.audit" in ROUTING_TABLE
        assert "compliance.consent.check" in ROUTING_TABLE
        assert "compliance.reporting.generate" in ROUTING_TABLE
