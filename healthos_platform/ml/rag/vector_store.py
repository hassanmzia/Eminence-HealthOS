"""
Eminence HealthOS — Clinical Vector Store (Qdrant)

Async wrapper around Qdrant for managing clinical knowledge collections:
  - clinical_guidelines
  - drug_information
  - icd10_codes
  - clinical_protocols
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

import structlog

from healthos_platform.config import get_settings
from healthos_platform.ml.rag.embeddings import EmbeddingService

logger = structlog.get_logger()

# ── Pre-defined clinical collections ──────────────────────────────────────────
CLINICAL_COLLECTIONS = [
    "clinical_guidelines",
    "drug_information",
    "icd10_codes",
    "clinical_protocols",
]


@dataclass
class SearchResult:
    """A single search result returned by the vector store."""

    id: str
    text: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)


class ClinicalVectorStore:
    """
    Async Qdrant vector store purpose-built for clinical knowledge retrieval.

    Parameters
    ----------
    qdrant_url : str | None
        Qdrant server URL.  Defaults to ``settings.qdrant_url``.
    embedding_service : EmbeddingService | None
        Embedding service instance.  A default one is created if omitted.
    """

    def __init__(
        self,
        qdrant_url: str | None = None,
        embedding_service: EmbeddingService | None = None,
    ) -> None:
        settings = get_settings()
        self._qdrant_url = qdrant_url or settings.qdrant_url
        self._embedding_service = embedding_service or EmbeddingService()
        self._client: Any | None = None

    # ------------------------------------------------------------------
    # Client lifecycle
    # ------------------------------------------------------------------

    async def _get_client(self):
        """Lazy-initialise the async Qdrant client."""
        if self._client is None:
            from qdrant_client import AsyncQdrantClient

            self._client = AsyncQdrantClient(url=self._qdrant_url, timeout=30)
            logger.info("clinical_vector_store.connected", url=self._qdrant_url)
        return self._client

    async def close(self) -> None:
        """Shut down the Qdrant client connection."""
        if self._client is not None:
            await self._client.close()
            self._client = None
            logger.info("clinical_vector_store.closed")

    # ------------------------------------------------------------------
    # Collection management
    # ------------------------------------------------------------------

    async def create_collection(
        self,
        name: str,
        vector_size: int | None = None,
    ) -> None:
        """
        Idempotent collection creation.

        If the collection already exists this is a no-op.

        Parameters
        ----------
        name : str
            Collection name.
        vector_size : int | None
            Embedding dimension.  Defaults to the dimension reported by the
            active ``EmbeddingService``.
        """
        from qdrant_client.models import Distance, VectorParams

        client = await self._get_client()
        collections = await client.get_collections()
        existing = {c.name for c in collections.collections}

        if name in existing:
            logger.debug("clinical_vector_store.collection.exists", collection=name)
            return

        size = vector_size or self._embedding_service.dimension
        await client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=size, distance=Distance.COSINE),
        )
        logger.info(
            "clinical_vector_store.collection.created",
            collection=name,
            vector_size=size,
        )

    async def ensure_clinical_collections(self) -> None:
        """Create all pre-defined clinical collections (idempotent)."""
        for name in CLINICAL_COLLECTIONS:
            await self.create_collection(name)

    async def delete_collection(self, name: str) -> None:
        """Delete a collection entirely."""
        client = await self._get_client()
        await client.delete_collection(collection_name=name)
        logger.info("clinical_vector_store.collection.deleted", collection=name)

    # ------------------------------------------------------------------
    # Document operations
    # ------------------------------------------------------------------

    async def upsert_documents(
        self,
        collection: str,
        documents: list[dict[str, Any]],
    ) -> int:
        """
        Upsert documents into a collection.

        Each document dict must contain:
          - ``id`` (str | int): unique document identifier
          - ``text`` (str): the document body to embed
          - ``metadata`` (dict): arbitrary metadata (source, category,
            icd10_codes, …)

        Parameters
        ----------
        collection : str
            Target collection name.
        documents : list[dict]
            Documents to upsert.

        Returns
        -------
        int
            Number of documents upserted.
        """
        if not documents:
            return 0

        from qdrant_client.models import PointStruct

        client = await self._get_client()

        # Embed all texts in one batch
        texts = [doc["text"] for doc in documents]
        vectors = self._embedding_service.embed_batch(texts)

        points = []
        for doc, vector in zip(documents, vectors):
            doc_id = doc["id"]
            # Qdrant accepts str UUIDs or ints as point IDs
            if isinstance(doc_id, str):
                try:
                    doc_id = str(uuid.UUID(doc_id))
                except ValueError:
                    # Use a deterministic UUID derived from the string id
                    doc_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, doc_id))

            payload = {
                "text": doc["text"],
                **doc.get("metadata", {}),
            }
            points.append(PointStruct(id=doc_id, vector=vector, payload=payload))

        # Qdrant supports batched upserts
        BATCH_SIZE = 100
        for i in range(0, len(points), BATCH_SIZE):
            batch = points[i : i + BATCH_SIZE]
            await client.upsert(collection_name=collection, points=batch)

        logger.info(
            "clinical_vector_store.upsert",
            collection=collection,
            count=len(points),
        )
        return len(points)

    async def delete_documents(
        self,
        collection: str,
        ids: list[str],
    ) -> None:
        """
        Delete documents by ID from a collection.

        Parameters
        ----------
        collection : str
            Target collection.
        ids : list[str]
            Document IDs to remove.
        """
        from qdrant_client.models import PointIdsList

        client = await self._get_client()

        # Normalise IDs the same way we do during upsert
        normalised: list[str] = []
        for doc_id in ids:
            try:
                normalised.append(str(uuid.UUID(doc_id)))
            except ValueError:
                normalised.append(str(uuid.uuid5(uuid.NAMESPACE_DNS, doc_id)))

        await client.delete(
            collection_name=collection,
            points_selector=PointIdsList(points=normalised),
        )
        logger.info(
            "clinical_vector_store.delete",
            collection=collection,
            count=len(normalised),
        )

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    async def search(
        self,
        collection: str,
        query_text: str,
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
        score_threshold: float = 0.0,
    ) -> list[SearchResult]:
        """
        Semantic search over a clinical collection.

        Parameters
        ----------
        collection : str
            Collection to search.
        query_text : str
            Natural-language query.
        top_k : int
            Maximum number of results.
        filters : dict | None
            Key-value payload filters (exact match).
        score_threshold : float
            Minimum cosine similarity score.

        Returns
        -------
        list[SearchResult]
            Ranked results with text, score, and metadata.
        """
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        client = await self._get_client()
        query_vector = self._embedding_service.embed_text(query_text)

        qdrant_filter = None
        if filters:
            conditions = [
                FieldCondition(key=k, match=MatchValue(value=v))
                for k, v in filters.items()
            ]
            qdrant_filter = Filter(must=conditions)

        hits = await client.search(
            collection_name=collection,
            query_vector=query_vector,
            query_filter=qdrant_filter,
            limit=top_k,
            score_threshold=score_threshold,
        )

        results = []
        for hit in hits:
            payload = hit.payload or {}
            text = payload.pop("text", "")
            results.append(
                SearchResult(
                    id=str(hit.id),
                    text=text,
                    score=hit.score,
                    metadata=payload,
                )
            )

        logger.info(
            "clinical_vector_store.search",
            collection=collection,
            query_length=len(query_text),
            results=len(results),
        )
        return results

    async def get_collection_info(self, name: str) -> dict[str, Any]:
        """Return point count and configuration for a collection."""
        client = await self._get_client()
        info = await client.get_collection(collection_name=name)
        return {
            "name": name,
            "points_count": info.points_count,
            "vectors_count": info.vectors_count,
            "status": info.status.value if info.status else "unknown",
        }
