"""
Eminence HealthOS — Clinical RAG Pipeline Orchestrator

End-to-end Retrieval-Augmented Generation for telehealth agents:
  1. Embed the user query
  2. Search Qdrant for relevant clinical documents
  3. Assemble retrieved context
  4. Call the LLM via the platform router with source-attributed answers
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import structlog

from healthos_platform.ml.llm.router import LLMRequest, LLMResponse, llm_router
from healthos_platform.ml.rag.embeddings import EmbeddingService
from healthos_platform.ml.rag.vector_store import (
    CLINICAL_COLLECTIONS,
    ClinicalVectorStore,
    SearchResult,
)

logger = structlog.get_logger()

# ── Clinical system prompt ────────────────────────────────────────────────────

CLINICAL_SYSTEM_PROMPT = (
    "You are a clinical knowledge assistant integrated into the Eminence HealthOS "
    "telehealth platform. Your role is to help healthcare providers quickly retrieve "
    "and synthesise evidence-based clinical information.\n\n"
    "Guidelines:\n"
    "- Base your answers strictly on the provided context documents.\n"
    "- Cite specific sources using [Source N] notation so providers can verify.\n"
    "- If the context is insufficient to answer confidently, say so explicitly.\n"
    "- Flag any potential drug interactions, contraindications, or safety concerns.\n"
    "- Use standard medical terminology but keep explanations concise.\n"
    "- Never fabricate clinical data or recommendations beyond what the sources support.\n"
    "- Include relevant ICD-10 codes when available in the source material.\n"
    "- Note the evidence level / guideline source when available."
)


# ── Response dataclass ────────────────────────────────────────────────────────


@dataclass
class SourceDocument:
    """A retrieved document included as evidence for the answer."""

    id: str
    text: str
    score: float
    collection: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RAGResponse:
    """Complete response from the RAG pipeline."""

    answer: str
    sources: list[SourceDocument] = field(default_factory=list)
    confidence: float = 0.0
    query: str = ""
    collection: str = ""
    llm_model: str = ""
    usage: dict[str, int] = field(default_factory=dict)


# ── Pipeline ──────────────────────────────────────────────────────────────────


class ClinicalRAGPipeline:
    """
    Orchestrates retrieval-augmented generation over clinical knowledge.

    Parameters
    ----------
    vector_store : ClinicalVectorStore | None
        Vector store instance (created automatically if omitted).
    embedding_service : EmbeddingService | None
        Shared embedding service (created automatically if omitted).
    default_collection : str
        Default Qdrant collection for searches.
    """

    def __init__(
        self,
        vector_store: ClinicalVectorStore | None = None,
        embedding_service: EmbeddingService | None = None,
        default_collection: str = "clinical_guidelines",
    ) -> None:
        self._embedding_service = embedding_service or EmbeddingService()
        self._vector_store = vector_store or ClinicalVectorStore(
            embedding_service=self._embedding_service,
        )
        self.default_collection = default_collection

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def retrieve_and_generate(
        self,
        query: str,
        collection: str | None = None,
        context: str | None = None,
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> RAGResponse:
        """
        Full RAG pipeline: retrieve relevant documents then generate an answer.

        Parameters
        ----------
        query : str
            The clinical question.
        collection : str | None
            Qdrant collection to search (defaults to ``self.default_collection``).
        context : str | None
            Optional extra context (e.g. patient history) prepended to the prompt.
        top_k : int
            Number of documents to retrieve.
        filters : dict | None
            Payload-level filters for the vector search.
        temperature : float
            LLM sampling temperature.
        max_tokens : int
            Maximum tokens in the generated answer.

        Returns
        -------
        RAGResponse
            The generated answer together with source documents and confidence.
        """
        target_collection = collection or self.default_collection

        # 1. Retrieve
        search_results = await self._retrieve(
            query=query,
            collection=target_collection,
            top_k=top_k,
            filters=filters,
        )

        # 2. Build prompt context from retrieved documents
        context_block = self._assemble_context(search_results, extra_context=context)

        # 3. Generate via LLM router
        llm_response = await self._generate(
            query=query,
            context_block=context_block,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        # 4. Compute a naive confidence score (average retrieval similarity)
        confidence = self._compute_confidence(search_results)

        # 5. Package sources
        sources = [
            SourceDocument(
                id=r.id,
                text=r.text,
                score=r.score,
                collection=target_collection,
                metadata=r.metadata,
            )
            for r in search_results
        ]

        return RAGResponse(
            answer=llm_response.content,
            sources=sources,
            confidence=confidence,
            query=query,
            collection=target_collection,
            llm_model=llm_response.model,
            usage=llm_response.usage,
        )

    async def retrieve_only(
        self,
        query: str,
        collection: str | None = None,
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        """
        Retrieve relevant documents without LLM generation.

        Useful for debugging or when the caller wants raw search results.
        """
        target_collection = collection or self.default_collection
        return await self._retrieve(
            query=query,
            collection=target_collection,
            top_k=top_k,
            filters=filters,
        )

    async def multi_collection_retrieve_and_generate(
        self,
        query: str,
        collections: list[str] | None = None,
        context: str | None = None,
        top_k_per_collection: int = 3,
        filters: dict[str, Any] | None = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> RAGResponse:
        """
        Search across multiple collections, merge results, then generate.

        Parameters
        ----------
        collections : list[str] | None
            Collections to search.  Defaults to all ``CLINICAL_COLLECTIONS``.
        top_k_per_collection : int
            Results per collection before merging.
        """
        target_collections = collections or CLINICAL_COLLECTIONS

        # Retrieve from each collection
        all_results: list[tuple[str, SearchResult]] = []
        for coll in target_collections:
            try:
                results = await self._retrieve(
                    query=query, collection=coll, top_k=top_k_per_collection, filters=filters
                )
                for r in results:
                    all_results.append((coll, r))
            except Exception as exc:
                logger.warning(
                    "rag.multi_collection.skip",
                    collection=coll,
                    error=str(exc),
                )

        # Sort by score descending, take top results
        all_results.sort(key=lambda x: x[1].score, reverse=True)
        top_results = all_results[: top_k_per_collection * 2]

        # Assemble context
        context_lines: list[str] = []
        if context:
            context_lines.append(f"Additional context:\n{context}\n")
        for idx, (coll, result) in enumerate(top_results, 1):
            source_label = result.metadata.get("source", coll)
            context_lines.append(
                f"[Source {idx}] (collection: {coll}, source: {source_label}, "
                f"score: {result.score:.3f})\n{result.text}"
            )
        context_block = "\n\n".join(context_lines)

        # Generate
        llm_response = await self._generate(
            query=query,
            context_block=context_block,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        confidence = (
            sum(r.score for _, r in top_results) / len(top_results) if top_results else 0.0
        )

        sources = [
            SourceDocument(
                id=r.id,
                text=r.text,
                score=r.score,
                collection=coll,
                metadata=r.metadata,
            )
            for coll, r in top_results
        ]

        return RAGResponse(
            answer=llm_response.content,
            sources=sources,
            confidence=confidence,
            query=query,
            collection=",".join(target_collections),
            llm_model=llm_response.model,
            usage=llm_response.usage,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _retrieve(
        self,
        query: str,
        collection: str,
        top_k: int,
        filters: dict[str, Any] | None,
    ) -> list[SearchResult]:
        """Run vector search against a single collection."""
        results = await self._vector_store.search(
            collection=collection,
            query_text=query,
            top_k=top_k,
            filters=filters,
        )
        logger.info(
            "rag.retrieve",
            collection=collection,
            query_length=len(query),
            results=len(results),
        )
        return results

    @staticmethod
    def _assemble_context(
        results: list[SearchResult],
        extra_context: str | None = None,
    ) -> str:
        """Build the context block injected into the LLM prompt."""
        parts: list[str] = []
        if extra_context:
            parts.append(f"Additional context:\n{extra_context}\n")

        for idx, result in enumerate(results, 1):
            source_label = result.metadata.get("source", "unknown")
            category = result.metadata.get("category", "")
            header = f"[Source {idx}] (source: {source_label}"
            if category:
                header += f", category: {category}"
            header += f", relevance: {result.score:.3f})"
            parts.append(f"{header}\n{result.text}")

        return "\n\n".join(parts)

    @staticmethod
    async def _generate(
        query: str,
        context_block: str,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        """Call the LLM router with the assembled prompt."""
        user_message = (
            f"Clinical context documents:\n\n{context_block}\n\n---\n\n"
            f"Clinical question: {query}\n\n"
            "Provide a concise, evidence-based answer citing the source documents "
            "using [Source N] notation. If the provided context is insufficient, "
            "state that clearly."
        )

        request = LLMRequest(
            system=CLINICAL_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
            temperature=temperature,
            max_tokens=max_tokens,
        )

        response = await llm_router.complete(request)
        logger.info(
            "rag.generate",
            model=response.model,
            input_tokens=response.usage.get("input_tokens", 0),
            output_tokens=response.usage.get("output_tokens", 0),
        )
        return response

    @staticmethod
    def _compute_confidence(results: list[SearchResult]) -> float:
        """
        Derive a confidence score from retrieval similarities.

        Returns 0.0 when no results are found, otherwise the mean similarity
        of the top results clamped to [0, 1].
        """
        if not results:
            return 0.0
        avg = sum(r.score for r in results) / len(results)
        return max(0.0, min(1.0, avg))
