"""
Eminence HealthOS — Performance Benchmark & Load Test Suite
Validates response times, throughput, and concurrency under load.
Run with: pytest tests/performance/ -v --benchmark
"""

from __future__ import annotations

import asyncio
import statistics
import time
import uuid
from typing import Any

import pytest

from healthos_platform.agents.types import AgentInput, AgentStatus


# ── Configuration ────────────────────────────────────────────────────────────

CONCURRENT_USERS = 50
REQUESTS_PER_USER = 10
TARGET_P95_MS = 200  # Agent processing target: <200ms p95
TARGET_P99_MS = 500  # Agent processing target: <500ms p99
TARGET_THROUGHPUT_RPS = 100  # Minimum requests/second


# ── Helpers ──────────────────────────────────────────────────────────────────

def _input(context: dict) -> AgentInput:
    return AgentInput(
        org_id=uuid.uuid4(),
        trigger="benchmark",
        context=context,
    )


async def _timed_run(agent, input_data: AgentInput) -> tuple[float, AgentStatus]:
    """Run an agent and return (duration_ms, status)."""
    start = time.perf_counter()
    output = await agent.run(input_data)
    duration = (time.perf_counter() - start) * 1000
    return duration, output.status


def _compute_percentiles(latencies: list[float]) -> dict[str, float]:
    """Compute p50, p95, p99 from latency list."""
    sorted_lat = sorted(latencies)
    n = len(sorted_lat)
    return {
        "min": sorted_lat[0],
        "p50": sorted_lat[int(n * 0.5)],
        "p95": sorted_lat[int(n * 0.95)],
        "p99": sorted_lat[int(n * 0.99)],
        "max": sorted_lat[-1],
        "mean": statistics.mean(sorted_lat),
        "stdev": statistics.stdev(sorted_lat) if n > 1 else 0,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLE AGENT BENCHMARKS
# ═══════════════════════════════════════════════════════════════════════════════


class TestAgentLatency:
    """Benchmark individual agent response times."""

    @pytest.mark.asyncio
    async def test_cost_risk_insight_latency(self):
        from modules.analytics.agents.cost_risk_insight import CostRiskInsightAgent

        agent = CostRiskInsightAgent()
        latencies = []

        for _ in range(100):
            duration, status = await _timed_run(agent, _input({
                "action": "cost_drivers",
                "patient_count": 1000,
            }))
            assert status == AgentStatus.COMPLETED
            latencies.append(duration)

        stats = _compute_percentiles(latencies)
        assert stats["p95"] < TARGET_P95_MS, f"p95={stats['p95']:.1f}ms exceeds {TARGET_P95_MS}ms"
        assert stats["p99"] < TARGET_P99_MS, f"p99={stats['p99']:.1f}ms exceeds {TARGET_P99_MS}ms"

    @pytest.mark.asyncio
    async def test_executive_insight_latency(self):
        from modules.analytics.agents.executive_insight import ExecutiveInsightAgent

        agent = ExecutiveInsightAgent()
        latencies = []

        for _ in range(100):
            duration, status = await _timed_run(agent, _input({
                "action": "kpi_scorecard",
            }))
            assert status == AgentStatus.COMPLETED
            latencies.append(duration)

        stats = _compute_percentiles(latencies)
        assert stats["p95"] < TARGET_P95_MS, f"p95={stats['p95']:.1f}ms exceeds {TARGET_P95_MS}ms"

    @pytest.mark.asyncio
    async def test_all_executive_actions_latency(self):
        from modules.analytics.agents.executive_insight import ExecutiveInsightAgent

        agent = ExecutiveInsightAgent()
        actions = [
            "executive_summary",
            "kpi_scorecard",
            "strategic_brief",
            "trend_digest",
        ]
        results: dict[str, dict] = {}

        for action in actions:
            latencies = []
            for _ in range(50):
                duration, status = await _timed_run(agent, _input({"action": action}))
                assert status == AgentStatus.COMPLETED
                latencies.append(duration)
            results[action] = _compute_percentiles(latencies)

        for action, stats in results.items():
            assert stats["p95"] < TARGET_P95_MS, (
                f"{action}: p95={stats['p95']:.1f}ms exceeds {TARGET_P95_MS}ms"
            )


# ═══════════════════════════════════════════════════════════════════════════════
# CONCURRENT LOAD TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestConcurrentLoad:
    """Test agent performance under concurrent load."""

    @pytest.mark.asyncio
    async def test_concurrent_agent_execution(self):
        """Simulate N concurrent users each making M requests."""
        from modules.analytics.agents.cost_risk_insight import CostRiskInsightAgent

        agent = CostRiskInsightAgent()
        all_latencies: list[float] = []
        error_count = 0

        async def user_session():
            nonlocal error_count
            session_latencies = []
            for _ in range(REQUESTS_PER_USER):
                try:
                    duration, status = await _timed_run(agent, _input({
                        "action": "cost_drivers",
                        "patient_count": 500,
                    }))
                    session_latencies.append(duration)
                    if status != AgentStatus.COMPLETED:
                        error_count += 1
                except Exception:
                    error_count += 1
            return session_latencies

        start = time.perf_counter()
        results = await asyncio.gather(
            *[user_session() for _ in range(CONCURRENT_USERS)]
        )
        total_time = time.perf_counter() - start

        for session in results:
            all_latencies.extend(session)

        total_requests = CONCURRENT_USERS * REQUESTS_PER_USER
        throughput = total_requests / total_time
        error_rate = error_count / total_requests

        stats = _compute_percentiles(all_latencies)

        # Assertions
        assert error_rate < 0.01, f"Error rate {error_rate:.1%} exceeds 1%"
        assert throughput >= TARGET_THROUGHPUT_RPS, (
            f"Throughput {throughput:.0f} RPS below target {TARGET_THROUGHPUT_RPS}"
        )
        assert stats["p99"] < TARGET_P99_MS, (
            f"Concurrent p99={stats['p99']:.1f}ms exceeds {TARGET_P99_MS}ms"
        )

    @pytest.mark.asyncio
    async def test_mixed_workload(self):
        """Simulate mixed agent workload (multiple agent types concurrently)."""
        from modules.analytics.agents.cost_risk_insight import CostRiskInsightAgent
        from modules.analytics.agents.executive_insight import ExecutiveInsightAgent

        cost_agent = CostRiskInsightAgent()
        exec_agent = ExecutiveInsightAgent()

        workloads = [
            (cost_agent, {"action": "cost_drivers"}),
            (cost_agent, {"action": "risk_cost_correlation"}),
            (cost_agent, {"action": "opportunity_scan"}),
            (exec_agent, {"action": "executive_summary"}),
            (exec_agent, {"action": "kpi_scorecard"}),
            (exec_agent, {"action": "trend_digest"}),
        ]

        all_latencies: list[float] = []

        async def run_workload(agent, ctx):
            latencies = []
            for _ in range(20):
                duration, status = await _timed_run(agent, _input(ctx))
                assert status == AgentStatus.COMPLETED
                latencies.append(duration)
            return latencies

        results = await asyncio.gather(
            *[run_workload(agent, ctx) for agent, ctx in workloads]
        )

        for batch in results:
            all_latencies.extend(batch)

        stats = _compute_percentiles(all_latencies)
        assert stats["p95"] < TARGET_P95_MS


# ═══════════════════════════════════════════════════════════════════════════════
# MEMORY & RESOURCE BENCHMARKS
# ═══════════════════════════════════════════════════════════════════════════════


class TestResourceUsage:
    """Test that agents don't leak memory or resources."""

    @pytest.mark.asyncio
    async def test_agent_memory_stability(self):
        """Run many iterations and verify no unbounded growth."""
        import sys
        from modules.analytics.agents.executive_insight import ExecutiveInsightAgent

        agent = ExecutiveInsightAgent()

        # Warm up
        for _ in range(10):
            await agent.run(_input({"action": "executive_summary"}))

        # Measure baseline
        baseline_size = sys.getsizeof(agent)

        # Run many iterations
        for _ in range(500):
            await agent.run(_input({"action": "executive_summary"}))

        # Check agent object hasn't grown significantly
        final_size = sys.getsizeof(agent)
        growth = final_size - baseline_size
        assert growth < 1024, f"Agent object grew by {growth} bytes over 500 iterations"

    @pytest.mark.asyncio
    async def test_large_batch_processing(self):
        """Test agent handles large input without degradation."""
        from modules.analytics.agents.cost_risk_insight import CostRiskInsightAgent

        agent = CostRiskInsightAgent()

        # Large patient population
        duration, status = await _timed_run(agent, _input({
            "action": "cost_drivers",
            "patient_count": 100000,
            "period_months": 36,
        }))
        assert status == AgentStatus.COMPLETED
        assert duration < 100, f"Large batch took {duration:.1f}ms"

    @pytest.mark.asyncio
    async def test_intervention_all_models(self):
        """Benchmark all intervention models."""
        from modules.analytics.agents.cost_risk_insight import (
            CostRiskInsightAgent,
            INTERVENTION_MODELS,
        )

        agent = CostRiskInsightAgent()

        for key in INTERVENTION_MODELS:
            duration, status = await _timed_run(agent, _input({
                "action": "intervention_impact",
                "intervention": key,
                "patient_count": 1000,
                "current_costs": {
                    "ed_visits": 2500000,
                    "inpatient_admissions": 9000000,
                    "readmissions": 3600000,
                    "pharmacy": 2000000,
                    "specialist_visits": 1200000,
                },
            }))
            assert status == AgentStatus.COMPLETED
            assert duration < 50, f"Intervention {key} took {duration:.1f}ms"
