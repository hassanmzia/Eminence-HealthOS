"""
Eminence HealthOS — Embedding Service for Clinical RAG Pipeline

Generates vector embeddings for clinical text using configurable backends:
  1. Qdrant FastEmbed (default, no external API needed)
  2. Sentence-transformers local models
  3. LLM router passthrough (for future API-based embeddings)
"""

from __future__ import annotations

from typing import Any

import structlog

logger = structlog.get_logger()

# Default embedding model (FastEmbed-compatible, 384-dim)
DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"
DEFAULT_EMBEDDING_DIM = 384


class EmbeddingService:
    """
    Generates text embeddings for clinical documents and queries.

    Defaults to Qdrant's built-in FastEmbed library, which runs locally
    without any external API calls — ideal for PHI-sensitive workloads.

    Parameters
    ----------
    model_name : str
        Model identifier. Defaults to ``BAAI/bge-small-en-v1.5`` (384-dim).
    backend : str
        One of ``"fastembed"`` (default), ``"sentence-transformers"``, or
        ``"llm_router"`` (delegates to the platform LLM router).
    cache_dir : str | None
        Optional directory for caching downloaded model weights.
    """

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        backend: str = "fastembed",
        cache_dir: str | None = None,
    ) -> None:
        self.model_name = model_name
        self.backend = backend
        self.cache_dir = cache_dir
        self._model: Any = None
        self._dimension: int | None = None

        logger.info(
            "embedding_service.init",
            model=model_name,
            backend=backend,
        )

    # ------------------------------------------------------------------
    # Lazy model loading
    # ------------------------------------------------------------------

    def _load_model(self) -> None:
        """Lazy-load the embedding model on first use."""
        if self._model is not None:
            return

        if self.backend == "fastembed":
            self._load_fastembed()
        elif self.backend == "sentence-transformers":
            self._load_sentence_transformers()
        elif self.backend == "llm_router":
            # No model to load — we delegate to the LLM router at call time
            self._dimension = DEFAULT_EMBEDDING_DIM
        else:
            raise ValueError(f"Unknown embedding backend: {self.backend}")

    def _load_fastembed(self) -> None:
        """Initialise a FastEmbed ``TextEmbedding`` model."""
        try:
            from fastembed import TextEmbedding
        except ImportError as exc:
            raise ImportError(
                "fastembed is required for the fastembed backend. "
                "Install it with: pip install fastembed"
            ) from exc

        kwargs: dict[str, Any] = {"model_name": self.model_name}
        if self.cache_dir:
            kwargs["cache_dir"] = self.cache_dir

        self._model = TextEmbedding(**kwargs)
        # Infer dimension from a probe embedding
        probe = list(self._model.embed(["probe"]))[0]
        self._dimension = len(probe)
        logger.info(
            "embedding_service.fastembed.loaded",
            model=self.model_name,
            dimension=self._dimension,
        )

    def _load_sentence_transformers(self) -> None:
        """Initialise a sentence-transformers ``SentenceTransformer`` model."""
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise ImportError(
                "sentence-transformers is required for the sentence-transformers "
                "backend. Install it with: pip install sentence-transformers"
            ) from exc

        self._model = SentenceTransformer(self.model_name)
        self._dimension = self._model.get_sentence_embedding_dimension()
        logger.info(
            "embedding_service.sentence_transformers.loaded",
            model=self.model_name,
            dimension=self._dimension,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def dimension(self) -> int:
        """Return the embedding vector dimensionality."""
        self._load_model()
        assert self._dimension is not None
        return self._dimension

    def embed_text(self, text: str) -> list[float]:
        """
        Generate an embedding vector for a single piece of text.

        Parameters
        ----------
        text : str
            The input text to embed.

        Returns
        -------
        list[float]
            Embedding vector.
        """
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embedding vectors for a batch of texts.

        Parameters
        ----------
        texts : list[str]
            Input texts to embed.

        Returns
        -------
        list[list[float]]
            One embedding vector per input text.
        """
        if not texts:
            return []

        self._load_model()

        if self.backend == "fastembed":
            return self._embed_fastembed(texts)
        elif self.backend == "sentence-transformers":
            return self._embed_sentence_transformers(texts)
        elif self.backend == "llm_router":
            return self._embed_llm_router(texts)
        else:
            raise ValueError(f"Unknown embedding backend: {self.backend}")

    # ------------------------------------------------------------------
    # Backend-specific embedding logic
    # ------------------------------------------------------------------

    def _embed_fastembed(self, texts: list[str]) -> list[list[float]]:
        """Embed via FastEmbed."""
        embeddings = list(self._model.embed(texts))
        return [emb.tolist() if hasattr(emb, "tolist") else list(emb) for emb in embeddings]

    def _embed_sentence_transformers(self, texts: list[str]) -> list[list[float]]:
        """Embed via sentence-transformers."""
        embeddings = self._model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()

    def _embed_llm_router(self, texts: list[str]) -> list[list[float]]:
        """
        Placeholder for LLM-router-based embeddings.

        In practice, this would call an embedding endpoint through the
        platform's LLM router.  For now we fall back to FastEmbed so
        callers always get a usable result.
        """
        logger.warning(
            "embedding_service.llm_router.fallback",
            message="LLM router embeddings not yet implemented; falling back to FastEmbed",
        )
        # Transparent fallback
        fallback = EmbeddingService(
            model_name=self.model_name,
            backend="fastembed",
            cache_dir=self.cache_dir,
        )
        return fallback.embed_batch(texts)
