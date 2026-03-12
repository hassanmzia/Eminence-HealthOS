"""Imaging & Radiology module agents — DICOM ingestion, AI image analysis, radiology reports, workflow, critical findings."""


def register_imaging_agents() -> None:
    """Register all Imaging & Radiology agents with the platform registry."""
    from healthos_platform.orchestrator.registry import registry

    from .critical_finding_alert import CriticalFindingAlertAgent
    from .image_analysis import ImageAnalysisAgent
    from .imaging_ingestion import ImagingIngestionAgent
    from .imaging_workflow import ImagingWorkflowAgent
    from .radiology_report import RadiologyReportAgent

    registry.register(ImagingIngestionAgent())
    registry.register(ImageAnalysisAgent())
    registry.register(RadiologyReportAgent())
    registry.register(ImagingWorkflowAgent())
    registry.register(CriticalFindingAlertAgent())
