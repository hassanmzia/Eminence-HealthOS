"""
Eminence HealthOS — EHR Connector Framework

Provides pluggable connectors for syncing encounters and clinical data
with external EHR systems via FHIR R4 and HL7v2 protocols.

Usage:
    from healthos_platform.interop.ehr import (
        BaseEHRConnector,
        FHIRConnector,
        HL7v2Connector,
        EHRSyncService,
    )
"""

from healthos_platform.interop.ehr.base_connector import BaseEHRConnector
from healthos_platform.interop.ehr.fhir_connector import FHIRConnector
from healthos_platform.interop.ehr.hl7v2_connector import HL7v2Connector
from healthos_platform.interop.ehr.sync_service import EHRSyncService

__all__ = [
    "BaseEHRConnector",
    "FHIRConnector",
    "HL7v2Connector",
    "EHRSyncService",
]
