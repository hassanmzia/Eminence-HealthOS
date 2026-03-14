"""
Eminence HealthOS — Clinical RAG (Retrieval-Augmented Generation) Module

Provides a complete pipeline for clinical knowledge retrieval used by
telehealth agents:

    from healthos_platform.ml.rag import (
        ClinicalRAGPipeline,
        ClinicalVectorStore,
        EmbeddingService,
    )

    pipeline = ClinicalRAGPipeline()
    response = await pipeline.retrieve_and_generate(
        query="What are the JNC-8 guidelines for stage 2 hypertension?",
        collection="clinical_guidelines",
    )
"""

from healthos_platform.ml.rag.embeddings import EmbeddingService
from healthos_platform.ml.rag.ingest import (
    chunk_text,
    ingest_clinical_guidelines,
    ingest_clinical_protocols,
    ingest_drug_database,
    ingest_icd10_codes,
)
from healthos_platform.ml.rag.pipeline import (
    ClinicalRAGPipeline,
    RAGResponse,
    SourceDocument,
)
from healthos_platform.ml.rag.vector_store import (
    CLINICAL_COLLECTIONS,
    ClinicalVectorStore,
    SearchResult,
)

__all__ = [
    # Core classes
    "ClinicalRAGPipeline",
    "ClinicalVectorStore",
    "EmbeddingService",
    # Data classes
    "RAGResponse",
    "SearchResult",
    "SourceDocument",
    # Ingestion helpers
    "chunk_text",
    "ingest_clinical_guidelines",
    "ingest_clinical_protocols",
    "ingest_drug_database",
    "ingest_icd10_codes",
    # Constants
    "CLINICAL_COLLECTIONS",
]
