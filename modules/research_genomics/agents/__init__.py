"""Research & Genomics module agents — clinical trial matching, de-identification, research cohorts, pharmacogenomics, genetic risk."""


def register_research_genomics_agents() -> None:
    """Register all Research & Genomics agents with the platform registry."""
    from healthos_platform.orchestrator.registry import registry

    from .clinical_trial_matching import ClinicalTrialMatchingAgent
    from .deidentification import DeIdentificationAgent
    from .genetic_risk import GeneticRiskAgent
    from .pharmacogenomics import PharmacogenomicsAgent
    from .research_cohort import ResearchCohortAgent

    registry.register(ClinicalTrialMatchingAgent())
    registry.register(DeIdentificationAgent())
    registry.register(ResearchCohortAgent())
    registry.register(PharmacogenomicsAgent())
    registry.register(GeneticRiskAgent())
