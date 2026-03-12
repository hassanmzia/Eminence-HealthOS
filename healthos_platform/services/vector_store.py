"""
Eminence HealthOS — Qdrant Vector Store & RAG Pipeline
Provides semantic search over clinical documents, patient notes, care plans,
and medical knowledge bases using vector embeddings.
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog

from healthos_platform.config import get_settings

logger = structlog.get_logger()

_client = None


async def get_qdrant_client():
    """Get or create the Qdrant async client."""
    global _client
    if _client is None:
        from qdrant_client import AsyncQdrantClient

        settings = get_settings()
        _client = AsyncQdrantClient(url=settings.qdrant_url, timeout=30)
        logger.info("qdrant.connected", url=settings.qdrant_url)
    return _client


async def close_qdrant():
    """Close the Qdrant client."""
    global _client
    if _client is not None:
        await _client.close()
        _client = None
        logger.info("qdrant.closed")


# ═══════════════════════════════════════════════════════════════════════════════
# Collections
# ═══════════════════════════════════════════════════════════════════════════════

COLLECTION_CLINICAL_NOTES = "clinical_notes"
COLLECTION_CARE_PLANS = "care_plans"
COLLECTION_MEDICAL_KNOWLEDGE = "medical_knowledge"
COLLECTION_PATIENT_SUMMARIES = "patient_summaries"

EMBEDDING_DIM = 384  # sentence-transformers default (all-MiniLM-L6-v2)


class VectorStore:
    """
    High-level vector store operations for HealthOS.
    Uses sentence-transformers for embeddings and Qdrant for storage/search.
    """

    def __init__(self) -> None:
        self._embedder = None

    def _get_embedder(self):
        """Lazy-load the sentence transformer model."""
        if self._embedder is None:
            from sentence_transformers import SentenceTransformer

            self._embedder = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("vectorstore.embedder.loaded", model="all-MiniLM-L6-v2")
        return self._embedder

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Compute embeddings for a list of texts."""
        embedder = self._get_embedder()
        return embedder.encode(texts, normalize_embeddings=True).tolist()

    def embed_single(self, text: str) -> list[float]:
        """Compute embedding for a single text."""
        return self.embed([text])[0]

    # ── Collection Management ─────────────────────────────────────────────

    async def ensure_collections(self) -> None:
        """Create all required collections if they don't exist."""
        from qdrant_client.models import Distance, VectorParams

        client = await get_qdrant_client()
        collections = await client.get_collections()
        existing = {c.name for c in collections.collections}

        for collection_name in [
            COLLECTION_CLINICAL_NOTES,
            COLLECTION_CARE_PLANS,
            COLLECTION_MEDICAL_KNOWLEDGE,
            COLLECTION_PATIENT_SUMMARIES,
        ]:
            if collection_name not in existing:
                await client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
                )
                logger.info("qdrant.collection.created", collection=collection_name)

    # ── Indexing ──────────────────────────────────────────────────────────

    async def index_document(
        self,
        collection: str,
        doc_id: str,
        text: str,
        metadata: dict[str, Any],
    ) -> None:
        """Index a single document with its embedding."""
        from qdrant_client.models import PointStruct

        client = await get_qdrant_client()
        vector = self.embed_single(text)

        await client.upsert(
            collection_name=collection,
            points=[
                PointStruct(
                    id=doc_id,
                    vector=vector,
                    payload={"text": text, **metadata},
                )
            ],
        )

    async def index_clinical_note(
        self,
        note_id: str,
        patient_id: str,
        org_id: str,
        note_text: str,
        note_type: str = "progress_note",
        provider_id: str | None = None,
    ) -> None:
        """Index a clinical note for semantic search."""
        await self.index_document(
            collection=COLLECTION_CLINICAL_NOTES,
            doc_id=note_id,
            text=note_text,
            metadata={
                "patient_id": patient_id,
                "org_id": org_id,
                "note_type": note_type,
                "provider_id": provider_id or "",
            },
        )
        logger.info("vectorstore.note.indexed", note_id=note_id, patient_id=patient_id)

    async def index_care_plan(
        self,
        plan_id: str,
        patient_id: str,
        org_id: str,
        plan_text: str,
        plan_type: str = "treatment",
    ) -> None:
        """Index a care plan for retrieval."""
        await self.index_document(
            collection=COLLECTION_CARE_PLANS,
            doc_id=plan_id,
            text=plan_text,
            metadata={
                "patient_id": patient_id,
                "org_id": org_id,
                "plan_type": plan_type,
            },
        )

    async def index_knowledge(
        self,
        doc_id: str,
        text: str,
        source: str,
        category: str,
    ) -> None:
        """Index medical knowledge base content."""
        await self.index_document(
            collection=COLLECTION_MEDICAL_KNOWLEDGE,
            doc_id=doc_id,
            text=text,
            metadata={"source": source, "category": category},
        )

    # ── Search ────────────────────────────────────────────────────────────

    async def search(
        self,
        collection: str,
        query: str,
        limit: int = 5,
        filters: dict[str, Any] | None = None,
        score_threshold: float = 0.5,
    ) -> list[dict[str, Any]]:
        """Semantic search across a collection."""
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        client = await get_qdrant_client()
        query_vector = self.embed_single(query)

        # Build filters
        qdrant_filter = None
        if filters:
            conditions = []
            for key, value in filters.items():
                conditions.append(FieldCondition(key=key, match=MatchValue(value=value)))
            qdrant_filter = Filter(must=conditions)

        results = await client.search(
            collection_name=collection,
            query_vector=query_vector,
            query_filter=qdrant_filter,
            limit=limit,
            score_threshold=score_threshold,
        )

        return [
            {
                "id": str(hit.id),
                "score": hit.score,
                "text": hit.payload.get("text", ""),
                "metadata": {k: v for k, v in hit.payload.items() if k != "text"},
            }
            for hit in results
        ]

    async def search_clinical_notes(
        self, query: str, patient_id: str | None = None, org_id: str | None = None, limit: int = 5
    ) -> list[dict[str, Any]]:
        """Search clinical notes with optional patient/org scoping."""
        filters = {}
        if patient_id:
            filters["patient_id"] = patient_id
        if org_id:
            filters["org_id"] = org_id
        return await self.search(COLLECTION_CLINICAL_NOTES, query, limit=limit, filters=filters or None)

    async def search_medical_knowledge(self, query: str, category: str | None = None, limit: int = 5) -> list[dict[str, Any]]:
        """Search the medical knowledge base."""
        filters = {"category": category} if category else None
        return await self.search(COLLECTION_MEDICAL_KNOWLEDGE, query, limit=limit, filters=filters)

    async def search_care_plans(
        self, query: str, patient_id: str | None = None, limit: int = 5
    ) -> list[dict[str, Any]]:
        """Search care plans."""
        filters = {"patient_id": patient_id} if patient_id else None
        return await self.search(COLLECTION_CARE_PLANS, query, limit=limit, filters=filters)


# ═══════════════════════════════════════════════════════════════════════════════
# RAG Pipeline
# ═══════════════════════════════════════════════════════════════════════════════


class RAGPipeline:
    """
    Retrieval-Augmented Generation pipeline for clinical queries.
    Combines vector search with LLM generation for contextual answers.
    """

    def __init__(self, vector_store: VectorStore | None = None):
        self.store = vector_store or VectorStore()

    async def retrieve_context(
        self,
        query: str,
        patient_id: str | None = None,
        org_id: str | None = None,
        max_chunks: int = 5,
    ) -> list[dict[str, Any]]:
        """Retrieve relevant context chunks for a query."""
        results = []

        # Search clinical notes for patient-specific context
        if patient_id:
            notes = await self.store.search_clinical_notes(
                query, patient_id=patient_id, org_id=org_id, limit=max_chunks
            )
            results.extend(notes)

        # Search medical knowledge base
        knowledge = await self.store.search_medical_knowledge(query, limit=max_chunks)
        results.extend(knowledge)

        # Sort by relevance and deduplicate
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:max_chunks]

    async def generate_answer(
        self,
        query: str,
        patient_id: str | None = None,
        org_id: str | None = None,
    ) -> dict[str, Any]:
        """RAG: retrieve context + generate LLM answer."""
        # Retrieve relevant context
        context_chunks = await self.retrieve_context(query, patient_id=patient_id, org_id=org_id)

        # Build context string
        context_text = "\n\n".join(
            f"[Source: {c['metadata'].get('source', c['metadata'].get('note_type', 'unknown'))}]\n{c['text']}"
            for c in context_chunks
        )

        # Generate answer using Anthropic
        settings = get_settings()
        if settings.anthropic_api_key:
            import anthropic

            client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
            response = client.messages.create(
                model=settings.default_llm_model,
                max_tokens=1024,
                system=(
                    "You are a clinical decision support assistant for HealthOS. "
                    "Answer questions using the provided clinical context. "
                    "Be precise, evidence-based, and flag any uncertainties. "
                    "Always note when information may be incomplete."
                ),
                messages=[
                    {
                        "role": "user",
                        "content": f"Context:\n{context_text}\n\nQuestion: {query}",
                    }
                ],
            )
            answer = response.content[0].text
        else:
            answer = f"[LLM not configured] Retrieved {len(context_chunks)} relevant context chunks for: {query}"

        return {
            "query": query,
            "answer": answer,
            "sources": [
                {"id": c["id"], "score": c["score"], "metadata": c["metadata"]}
                for c in context_chunks
            ],
            "context_chunks_used": len(context_chunks),
        }


# Module-level instances
vector_store = VectorStore()
rag_pipeline = RAGPipeline(vector_store)
