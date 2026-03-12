"""Ambient AI Documentation agents — automatic clinical documentation from patient-provider conversations."""


def register_ambient_ai_agents() -> None:
    """Register all Ambient AI agents with the platform registry."""
    from healthos_platform.orchestrator.registry import registry

    from .ambient_listening import AmbientListeningAgent
    from .auto_coding import AutoCodingAgent
    from .provider_attestation import ProviderAttestationAgent
    from .soap_note_generator import SOAPNoteGeneratorAgent
    from .speaker_diarization import SpeakerDiarizationAgent

    registry.register(AmbientListeningAgent())
    registry.register(SpeakerDiarizationAgent())
    registry.register(SOAPNoteGeneratorAgent())
    registry.register(AutoCodingAgent())
    registry.register(ProviderAttestationAgent())
