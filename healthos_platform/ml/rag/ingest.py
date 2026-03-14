"""
Eminence HealthOS — Clinical Document Ingestion Utilities

Handles chunking, metadata extraction, and batch ingestion of clinical
content into the Qdrant vector store.
"""

from __future__ import annotations

import hashlib
import re
import uuid
from typing import Any

import structlog

from healthos_platform.ml.rag.vector_store import ClinicalVectorStore

logger = structlog.get_logger()

# ── Chunking defaults ─────────────────────────────────────────────────────────

DEFAULT_CHUNK_SIZE = 500  # target tokens (approx 4 chars/token)
DEFAULT_CHUNK_OVERLAP = 50  # overlap tokens
CHARS_PER_TOKEN = 4  # rough estimate for English text


# ── Text chunking ─────────────────────────────────────────────────────────────


def chunk_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[str]:
    """
    Split text into overlapping chunks of approximately ``chunk_size`` tokens.

    Uses paragraph / sentence boundaries where possible to avoid splitting
    mid-sentence.

    Parameters
    ----------
    text : str
        Input text.
    chunk_size : int
        Target size in tokens (approximate).
    chunk_overlap : int
        Number of overlapping tokens between consecutive chunks.

    Returns
    -------
    list[str]
        List of text chunks.
    """
    if not text or not text.strip():
        return []

    char_limit = chunk_size * CHARS_PER_TOKEN
    overlap_chars = chunk_overlap * CHARS_PER_TOKEN

    # Split into paragraphs first
    paragraphs = re.split(r"\n\s*\n", text.strip())

    chunks: list[str] = []
    current_chunk: list[str] = []
    current_length = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        para_len = len(para)

        # If a single paragraph exceeds the limit, split it by sentences
        if para_len > char_limit:
            # Flush current chunk first
            if current_chunk:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = []
                current_length = 0

            sentence_chunks = _split_paragraph_into_chunks(
                para, char_limit, overlap_chars
            )
            chunks.extend(sentence_chunks)
            continue

        # Would adding this paragraph exceed the limit?
        if current_length + para_len + 2 > char_limit and current_chunk:
            chunks.append("\n\n".join(current_chunk))
            # Keep last part for overlap
            overlap_text = current_chunk[-1] if current_chunk else ""
            current_chunk = []
            current_length = 0
            if overlap_text and len(overlap_text) <= overlap_chars:
                current_chunk.append(overlap_text)
                current_length = len(overlap_text)

        current_chunk.append(para)
        current_length += para_len + 2  # account for \n\n

    # Flush remaining
    if current_chunk:
        chunks.append("\n\n".join(current_chunk))

    return chunks


def _split_paragraph_into_chunks(
    paragraph: str,
    char_limit: int,
    overlap_chars: int,
) -> list[str]:
    """Split a long paragraph by sentence boundaries."""
    sentences = re.split(r"(?<=[.!?])\s+", paragraph)
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        if current_len + len(sentence) + 1 > char_limit and current:
            chunks.append(" ".join(current))
            # Overlap: keep last sentence(s) within budget
            overlap: list[str] = []
            overlap_len = 0
            for s in reversed(current):
                if overlap_len + len(s) + 1 > overlap_chars:
                    break
                overlap.insert(0, s)
                overlap_len += len(s) + 1
            current = overlap
            current_len = overlap_len

        current.append(sentence)
        current_len += len(sentence) + 1

    if current:
        chunks.append(" ".join(current))

    return chunks


# ── Metadata extraction ──────────────────────────────────────────────────────


def extract_metadata(
    text: str,
    default_source: str = "unknown",
    default_category: str = "general",
) -> dict[str, Any]:
    """
    Extract lightweight metadata from a clinical text chunk.

    Looks for section headers, ICD-10 codes, and drug names.
    """
    metadata: dict[str, Any] = {
        "source": default_source,
        "category": default_category,
    }

    # Try to extract a section header (first line if short)
    lines = text.strip().split("\n")
    if lines and len(lines[0]) < 120:
        metadata["section_header"] = lines[0].strip().rstrip(":")

    # Extract ICD-10 codes (pattern: letter + 2 digits + optional .digits)
    icd10_pattern = r"\b([A-Z]\d{2}(?:\.\d{1,4})?)\b"
    icd10_matches = re.findall(icd10_pattern, text)
    if icd10_matches:
        metadata["icd10_codes"] = list(set(icd10_matches))

    return metadata


def generate_document_id(text: str, collection: str, index: int = 0) -> str:
    """Produce a deterministic UUID for a document chunk."""
    hash_input = f"{collection}:{index}:{text[:200]}"
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, hashlib.md5(hash_input.encode()).hexdigest()))


# ── Ingestion functions ───────────────────────────────────────────────────────


async def ingest_clinical_guidelines(
    filepath_or_texts: str | list[str],
    collection: str = "clinical_guidelines",
    vector_store: ClinicalVectorStore | None = None,
    source: str = "clinical_guideline",
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> int:
    """
    Chunk and ingest clinical guideline text into the vector store.

    Parameters
    ----------
    filepath_or_texts : str | list[str]
        Either a file path to read, or a list of raw text strings.
    collection : str
        Target Qdrant collection.
    vector_store : ClinicalVectorStore | None
        Store instance; creates a default one if omitted.
    source : str
        Source label for metadata.
    chunk_size : int
        Target chunk size in tokens.
    chunk_overlap : int
        Chunk overlap in tokens.

    Returns
    -------
    int
        Number of chunks ingested.
    """
    store = vector_store or ClinicalVectorStore()

    # Resolve input
    if isinstance(filepath_or_texts, str):
        with open(filepath_or_texts, "r", encoding="utf-8") as fh:
            raw_texts = [fh.read()]
    else:
        raw_texts = filepath_or_texts

    # Ensure collection exists
    await store.create_collection(collection)

    documents: list[dict[str, Any]] = []
    for text_idx, raw_text in enumerate(raw_texts):
        chunks = chunk_text(raw_text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        for chunk_idx, chunk in enumerate(chunks):
            doc_id = generate_document_id(raw_text, collection, chunk_idx)
            meta = extract_metadata(chunk, default_source=source, default_category="guideline")
            documents.append(
                {
                    "id": doc_id,
                    "text": chunk,
                    "metadata": meta,
                }
            )

    count = await store.upsert_documents(collection, documents)
    logger.info(
        "ingest.clinical_guidelines",
        collection=collection,
        raw_texts=len(raw_texts),
        chunks=count,
    )
    return count


async def ingest_drug_database(
    filepath_or_records: str | list[dict[str, Any]],
    collection: str = "drug_information",
    vector_store: ClinicalVectorStore | None = None,
    source: str = "drug_database",
) -> int:
    """
    Ingest structured drug information records.

    Each record dict should contain at minimum:
      - ``name`` (str): drug name
      - ``description`` (str): drug description / interaction text

    Optional fields (folded into metadata):
      - ``category``, ``interactions``, ``contraindications``, ``icd10_codes``

    Parameters
    ----------
    filepath_or_records : str | list[dict]
        Path to a JSON file or a list of record dicts.
    collection : str
        Target collection.
    vector_store : ClinicalVectorStore | None
        Store instance.
    source : str
        Source label.

    Returns
    -------
    int
        Number of records ingested.
    """
    import json

    store = vector_store or ClinicalVectorStore()

    if isinstance(filepath_or_records, str):
        with open(filepath_or_records, "r", encoding="utf-8") as fh:
            records = json.load(fh)
    else:
        records = filepath_or_records

    await store.create_collection(collection)

    documents: list[dict[str, Any]] = []
    for idx, record in enumerate(records):
        name = record.get("name", f"drug_{idx}")
        description = record.get("description", "")
        if not description:
            continue

        # Build searchable text blob
        text_parts = [f"Drug: {name}", description]
        if record.get("interactions"):
            text_parts.append(f"Interactions: {record['interactions']}")
        if record.get("contraindications"):
            text_parts.append(f"Contraindications: {record['contraindications']}")
        text = "\n".join(text_parts)

        doc_id = generate_document_id(name, collection, idx)
        meta: dict[str, Any] = {
            "source": source,
            "category": record.get("category", "drug_information"),
            "drug_name": name,
        }
        if record.get("icd10_codes"):
            meta["icd10_codes"] = record["icd10_codes"]

        documents.append({"id": doc_id, "text": text, "metadata": meta})

    count = await store.upsert_documents(collection, documents)
    logger.info(
        "ingest.drug_database",
        collection=collection,
        records=len(records),
        ingested=count,
    )
    return count


async def ingest_icd10_codes(
    records: list[dict[str, str]],
    collection: str = "icd10_codes",
    vector_store: ClinicalVectorStore | None = None,
) -> int:
    """
    Ingest ICD-10 code records.

    Each record: ``{"code": "I10", "description": "Essential hypertension"}``
    """
    store = vector_store or ClinicalVectorStore()
    await store.create_collection(collection)

    documents: list[dict[str, Any]] = []
    for idx, rec in enumerate(records):
        code = rec.get("code", "")
        desc = rec.get("description", "")
        text = f"ICD-10 {code}: {desc}"
        doc_id = generate_document_id(code, collection, idx)
        documents.append(
            {
                "id": doc_id,
                "text": text,
                "metadata": {
                    "source": "icd10",
                    "category": "icd10_code",
                    "icd10_codes": [code],
                },
            }
        )

    count = await store.upsert_documents(collection, documents)
    logger.info("ingest.icd10_codes", collection=collection, count=count)
    return count


async def ingest_clinical_protocols(
    filepath_or_texts: str | list[str],
    collection: str = "clinical_protocols",
    vector_store: ClinicalVectorStore | None = None,
    source: str = "clinical_protocol",
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> int:
    """
    Chunk and ingest clinical protocol documents.

    Same interface as ``ingest_clinical_guidelines`` but targets the
    ``clinical_protocols`` collection with appropriate metadata.
    """
    return await ingest_clinical_guidelines(
        filepath_or_texts=filepath_or_texts,
        collection=collection,
        vector_store=vector_store,
        source=source,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
