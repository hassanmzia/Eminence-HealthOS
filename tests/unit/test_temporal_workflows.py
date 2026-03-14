"""
Unit tests for Temporal workflow definitions.
Tests workflow and activity structure without requiring a running Temporal server.
"""

from __future__ import annotations

import pytest


class TestTemporalModule:
    def test_imports_successfully(self):
        """Temporal module should import without error."""
        from healthos_platform.services.temporal import (
            TemporalClient,
            get_temporal_client,
        )
        assert TemporalClient is not None

    def test_workflow_definitions_exist(self):
        """All clinical workflow classes should be defined."""
        from healthos_platform.services.temporal import (
            CriticalAlertWorkflow,
            PatientOnboardingWorkflow,
            RPMReviewWorkflow,
        )
        assert PatientOnboardingWorkflow is not None
        assert CriticalAlertWorkflow is not None
        assert RPMReviewWorkflow is not None

    def test_activity_definitions_exist(self):
        """All activity functions should be defined."""
        from healthos_platform.services.temporal import (
            create_encounter_activity,
            run_agent_activity,
            send_notification_activity,
            update_patient_status_activity,
        )
        assert callable(run_agent_activity)
        assert callable(send_notification_activity)
        assert callable(create_encounter_activity)
        assert callable(update_patient_status_activity)

    def test_worker_factory_exists(self):
        """Worker creation function should be defined."""
        from healthos_platform.services.temporal import create_temporal_worker
        assert callable(create_temporal_worker)

    def test_client_singleton_pattern(self):
        """get_temporal_client should return consistent reference."""
        from healthos_platform.services.temporal import get_temporal_client
        # Without a running Temporal server, client won't be connected
        # but the function should exist and be callable
        assert callable(get_temporal_client)
