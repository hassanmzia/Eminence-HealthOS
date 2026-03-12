"""Tests for the Imaging & Radiology module agents."""

import uuid
import pytest

from healthos_platform.agents.types import AgentInput, AgentStatus

DEFAULT_ORG = uuid.UUID("00000000-0000-0000-0000-000000000001")
PATIENT_ID = uuid.UUID("00000000-0000-0000-0000-000000000099")


def _input(action: str, **extra) -> AgentInput:
    return AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=PATIENT_ID,
        trigger=f"imaging.{action}",
        context={"action": action, **extra},
    )


# ── Imaging Ingestion Agent ──────────────────────────────────────


class TestImagingIngestionAgent:
    @pytest.fixture
    def agent(self):
        from modules.imaging.agents.imaging_ingestion import ImagingIngestionAgent
        return ImagingIngestionAgent()

    @pytest.mark.asyncio
    async def test_ingest_study(self, agent):
        out = await agent.run(_input("ingest_study",
            modality="CR", body_part="CHEST", series_count=2, instance_count=2))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["modality"] == "CR"
        assert out.result["status"] == "received"

    @pytest.mark.asyncio
    async def test_ingest_ct(self, agent):
        out = await agent.run(_input("ingest_study",
            modality="CT", body_part="HEAD", series_count=3))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["modality"] == "CT"
        assert out.result["ai_analysis_supported"] is True

    @pytest.mark.asyncio
    async def test_validate_dicom(self, agent):
        out = await agent.run(_input("validate_dicom",
            study_uid="1.2.3.4", modality="CR"))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["all_passed"] is True

    @pytest.mark.asyncio
    async def test_query_studies(self, agent):
        out = await agent.run(_input("query_studies"))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["total_studies"] > 0

    @pytest.mark.asyncio
    async def test_route_study(self, agent):
        out = await agent.run(_input("route_study",
            study_id="STD-001", priority="stat"))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["assigned_worklist"] == "STAT"

    @pytest.mark.asyncio
    async def test_unknown_action(self, agent):
        out = await agent.run(_input("nonexistent"))
        assert out.status == AgentStatus.FAILED


# ── Image Analysis Agent ─────────────────────────────────────────


class TestImageAnalysisAgent:
    @pytest.fixture
    def agent(self):
        from modules.imaging.agents.image_analysis import ImageAnalysisAgent
        return ImageAnalysisAgent()

    @pytest.mark.asyncio
    async def test_analyze_chest_xray(self, agent):
        out = await agent.run(_input("analyze_image", study_type="chest_xray"))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["model_used"] == "CheXNet-v2"
        assert out.result["total_findings"] > 0

    @pytest.mark.asyncio
    async def test_analyze_ct_head(self, agent):
        out = await agent.run(_input("analyze_image", study_type="ct_head"))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["model_used"] == "DeepBleed-v1"

    @pytest.mark.asyncio
    async def test_detect_findings(self, agent):
        out = await agent.run(_input("detect_findings", study_type="chest_xray"))
        assert out.status == AgentStatus.COMPLETED
        assert "detections" in out.result

    @pytest.mark.asyncio
    async def test_compare_priors(self, agent):
        out = await agent.run(_input("compare_priors",
            current_study_id="STD-001", prior_study_id="STD-000"))
        assert out.status == AgentStatus.COMPLETED
        assert len(out.result["changes"]) > 0

    @pytest.mark.asyncio
    async def test_model_info(self, agent):
        out = await agent.run(_input("model_info"))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["total_models"] >= 5

    @pytest.mark.asyncio
    async def test_unknown_action(self, agent):
        out = await agent.run(_input("nonexistent"))
        assert out.status == AgentStatus.FAILED


# ── Radiology Report Agent ───────────────────────────────────────


class TestRadiologyReportAgent:
    @pytest.fixture
    def agent(self):
        from modules.imaging.agents.radiology_report import RadiologyReportAgent
        return RadiologyReportAgent()

    @pytest.mark.asyncio
    async def test_generate_report(self, agent):
        out = await agent.run(_input("generate_report", study_type="chest_xray"))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["report"]["status"] == "preliminary"
        assert out.result["report"]["ai_assisted"] is True

    @pytest.mark.asyncio
    async def test_generate_mammography_report(self, agent):
        out = await agent.run(_input("generate_report",
            study_type="mammography", birads_category=2))
        assert out.status == AgentStatus.COMPLETED
        assert "birads_category" in out.result["report"]

    @pytest.mark.asyncio
    async def test_addendum(self, agent):
        out = await agent.run(_input("addendum",
            report_id="RPT-001", addendum_text="Additional finding noted", author="Dr. Chen"))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["status"] == "addendum_added"

    @pytest.mark.asyncio
    async def test_structured_data(self, agent):
        out = await agent.run(_input("structured_data", report_id="RPT-001"))
        assert out.status == AgentStatus.COMPLETED
        assert len(out.result["structured_findings"]) > 0

    @pytest.mark.asyncio
    async def test_unknown_action(self, agent):
        out = await agent.run(_input("nonexistent"))
        assert out.status == AgentStatus.FAILED


# ── Imaging Workflow Agent ───────────────────────────────────────


class TestImagingWorkflowAgent:
    @pytest.fixture
    def agent(self):
        from modules.imaging.agents.imaging_workflow import ImagingWorkflowAgent
        return ImagingWorkflowAgent()

    @pytest.mark.asyncio
    async def test_assign_study(self, agent):
        out = await agent.run(_input("assign_study",
            study_id="STD-001", priority="urgent"))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["worklist"] == "URGENT"

    @pytest.mark.asyncio
    async def test_assign_critical_escalates(self, agent):
        out = await agent.run(_input("assign_study",
            study_id="STD-002", priority="routine", has_critical_ai_finding=True))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["priority"] == "stat"

    @pytest.mark.asyncio
    async def test_update_read_status(self, agent):
        out = await agent.run(_input("update_read_status",
            study_id="STD-001", new_status="read"))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["new_status"] == "read"

    @pytest.mark.asyncio
    async def test_worklist_summary(self, agent):
        out = await agent.run(_input("worklist_summary"))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["total_pending"] > 0

    @pytest.mark.asyncio
    async def test_sla_check(self, agent):
        out = await agent.run(_input("sla_check"))
        assert out.status == AgentStatus.COMPLETED
        assert "sla_breaches" in out.result

    @pytest.mark.asyncio
    async def test_unknown_action(self, agent):
        out = await agent.run(_input("nonexistent"))
        assert out.status == AgentStatus.FAILED


# ── Critical Finding Alert Agent ─────────────────────────────────


class TestCriticalFindingAlertAgent:
    @pytest.fixture
    def agent(self):
        from modules.imaging.agents.critical_finding_alert import CriticalFindingAlertAgent
        return CriticalFindingAlertAgent()

    @pytest.mark.asyncio
    async def test_evaluate_no_critical(self, agent):
        findings = [{"finding": "normal", "confidence": 0.95}]
        out = await agent.run(_input("evaluate_findings", findings=findings))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["critical_findings_count"] == 0

    @pytest.mark.asyncio
    async def test_evaluate_with_critical(self, agent):
        findings = [
            {"finding": "pneumothorax", "confidence": 0.92, "location": "right_lung"},
            {"finding": "normal_heart", "confidence": 0.95},
        ]
        out = await agent.run(_input("evaluate_findings", findings=findings))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["critical_findings_count"] == 1
        assert out.result["requires_escalation"] is True

    @pytest.mark.asyncio
    async def test_escalate_finding(self, agent):
        out = await agent.run(_input("escalate_finding",
            finding="pneumothorax", urgency="stat"))
        assert out.status == AgentStatus.COMPLETED
        assert len(out.result["notifications_sent"]) >= 3

    @pytest.mark.asyncio
    async def test_acknowledge_finding(self, agent):
        out = await agent.run(_input("acknowledge_finding",
            alert_id="ALERT-001", acknowledged_by="Dr. Rodriguez"))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["status"] == "acknowledged"
        assert out.result["acr_compliant"] is True

    @pytest.mark.asyncio
    async def test_critical_finding_log(self, agent):
        out = await agent.run(_input("critical_finding_log"))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["total_critical_findings"] > 0

    @pytest.mark.asyncio
    async def test_unknown_action(self, agent):
        out = await agent.run(_input("nonexistent"))
        assert out.status == AgentStatus.FAILED


# ── Registration & Routing ───────────────────────────────────────


class TestImagingRegistration:
    def test_register_imaging_agents(self):
        from modules.imaging.agents import register_imaging_agents
        from healthos_platform.orchestrator.registry import registry
        register_imaging_agents()
        for name in ["imaging_ingestion", "image_analysis", "radiology_report",
                      "imaging_workflow", "critical_finding_alert"]:
            assert registry.get(name) is not None, f"Agent '{name}' not registered"

    def test_imaging_routing_entries(self):
        from healthos_platform.orchestrator.router import ROUTING_TABLE
        imaging_events = [k for k in ROUTING_TABLE if k.startswith("imaging.")]
        assert len(imaging_events) >= 5, f"Expected >=5 imaging routes, got {len(imaging_events)}"
