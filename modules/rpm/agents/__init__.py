"""
Eminence HealthOS — RPM Module Agent Registration
"""

from modules.rpm.agents.adherence_monitoring import AdherenceMonitoringAgent
from modules.rpm.agents.anomaly_detection import AnomalyDetectionAgent
from modules.rpm.agents.device_ingestion import DeviceIngestionAgent
from modules.rpm.agents.risk_scoring import RiskScoringAgent
from modules.rpm.agents.trend_analysis import TrendAnalysisAgent
from modules.rpm.agents.vitals_normalization import VitalsNormalizationAgent


def register_rpm_agents() -> None:
    """Register all RPM agents with the global registry."""
    from healthos_platform.orchestrator.registry import registry

    registry.register(DeviceIngestionAgent())
    registry.register(VitalsNormalizationAgent())
    registry.register(AnomalyDetectionAgent())
    registry.register(RiskScoringAgent())
    registry.register(TrendAnalysisAgent())
    registry.register(AdherenceMonitoringAgent())
