"""
Clinical Embeddings and ChromaDB Integration
Provides semantic search over medical knowledge base using vector embeddings.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Configuration
CHROMA_HOST = os.getenv("CHROMA_HOST", "chromadb")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")


@dataclass
class SearchResult:
    """Result from vector search"""
    id: str
    content: str
    metadata: Dict[str, Any]
    score: float


class ClinicalEmbeddings:
    """
    Clinical knowledge embeddings using ChromaDB.
    Supports semantic search over guidelines, drug info, and medical literature.
    """

    def __init__(self):
        self._client = None
        self._embeddings_fn = None
        self._collections = {}
        self._initialized = False

    def _lazy_init(self):
        """Lazy initialization of ChromaDB client and embeddings"""
        if self._initialized:
            return

        try:
            import chromadb
            from chromadb.config import Settings

            # Try to connect to ChromaDB server
            try:
                self._client = chromadb.HttpClient(
                    host=CHROMA_HOST,
                    port=CHROMA_PORT,
                    settings=Settings(anonymized_telemetry=False)
                )
                self._client.heartbeat()
                logger.info(f"Connected to ChromaDB at {CHROMA_HOST}:{CHROMA_PORT}")
            except Exception as e:
                # Fall back to persistent local client
                logger.warning(f"ChromaDB server unavailable, using local: {e}")
                self._client = chromadb.PersistentClient(
                    path="/data/chroma",
                    settings=Settings(anonymized_telemetry=False)
                )

            # Initialize embedding function
            try:
                from chromadb.utils import embedding_functions
                self._embeddings_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name=EMBEDDING_MODEL
                )
            except Exception as e:
                logger.warning(f"SentenceTransformer unavailable, using default: {e}")
                self._embeddings_fn = None

            self._initialized = True

        except ImportError as e:
            logger.error(f"ChromaDB not installed: {e}")
            raise

    def _get_collection(self, name: str):
        """Get or create a collection"""
        self._lazy_init()

        if name not in self._collections:
            self._collections[name] = self._client.get_or_create_collection(
                name=name,
                embedding_function=self._embeddings_fn,
                metadata={"hnsw:space": "cosine"}
            )

        return self._collections[name]

    async def add_guidelines(self, guidelines: List[Dict[str, Any]]) -> int:
        """Add clinical guidelines to the vector store"""
        collection = self._get_collection("clinical_guidelines")

        ids = []
        documents = []
        metadatas = []

        for i, guideline in enumerate(guidelines):
            doc_id = guideline.get("id") or f"guideline_{i}"
            ids.append(doc_id)

            # Combine title and content for embedding
            content = f"{guideline.get('title', '')}\n\n{guideline.get('content', '')}"
            documents.append(content)

            metadatas.append({
                "title": guideline.get("title", ""),
                "condition": guideline.get("condition", ""),
                "icd10_codes": ",".join(guideline.get("icd10", [])),
                "cpt_codes": ",".join(guideline.get("cpt_codes", [])),
                "source": guideline.get("source", ""),
                "category": guideline.get("category", "general")
            })

        collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
        return len(ids)

    async def add_drug_info(self, drugs: List[Dict[str, Any]]) -> int:
        """Add drug information to the vector store"""
        collection = self._get_collection("drug_database")

        ids = []
        documents = []
        metadatas = []

        for drug in drugs:
            doc_id = drug.get("id") or drug.get("name", "").lower().replace(" ", "_")
            ids.append(doc_id)

            # Build comprehensive drug document
            content = f"""
            Drug: {drug.get('name', '')}
            Generic: {drug.get('generic_name', '')}
            Class: {drug.get('drug_class', '')}

            Indications: {drug.get('indications', '')}

            Dosing: {drug.get('dosing', '')}

            Contraindications: {drug.get('contraindications', '')}

            Side Effects: {drug.get('side_effects', '')}

            Interactions: {drug.get('interactions', '')}
            """
            documents.append(content)

            metadatas.append({
                "name": drug.get("name", ""),
                "generic_name": drug.get("generic_name", ""),
                "drug_class": drug.get("drug_class", ""),
                "controlled": str(drug.get("controlled", False)),
                "formulary_status": drug.get("formulary_status", ""),
            })

        collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
        return len(ids)

    async def add_icd10_codes(self, codes: List[Dict[str, Any]]) -> int:
        """Add ICD-10 codes to the vector store"""
        collection = self._get_collection("icd10_codes")

        ids = []
        documents = []
        metadatas = []

        for code_info in codes:
            code = code_info.get("code", "")
            ids.append(code)

            # Build searchable document
            content = f"""
            ICD-10 Code: {code}
            Description: {code_info.get('description', '')}
            Long Description: {code_info.get('long_description', '')}
            Category: {code_info.get('category', '')}
            Related Terms: {', '.join(code_info.get('related_terms', []))}
            """
            documents.append(content)

            metadatas.append({
                "code": code,
                "description": code_info.get("description", ""),
                "category": code_info.get("category", ""),
                "chapter": code_info.get("chapter", ""),
                "billable": str(code_info.get("billable", True))
            })

        collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
        return len(ids)

    async def search_guidelines(
        self,
        query: str,
        n_results: int = 5,
        filter_condition: str = None
    ) -> List[SearchResult]:
        """Semantic search over clinical guidelines"""
        collection = self._get_collection("clinical_guidelines")

        where_filter = None
        if filter_condition:
            where_filter = {"condition": filter_condition}

        results = collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where_filter
        )

        return self._format_results(results)

    async def search_drugs(
        self,
        query: str,
        n_results: int = 5,
        drug_class: str = None
    ) -> List[SearchResult]:
        """Semantic search over drug database"""
        collection = self._get_collection("drug_database")

        where_filter = None
        if drug_class:
            where_filter = {"drug_class": drug_class}

        results = collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where_filter
        )

        return self._format_results(results)

    async def search_icd10(
        self,
        query: str,
        n_results: int = 10,
        category: str = None
    ) -> List[SearchResult]:
        """Semantic search over ICD-10 codes"""
        collection = self._get_collection("icd10_codes")

        where_filter = None
        if category:
            where_filter = {"category": category}

        results = collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where_filter
        )

        return self._format_results(results)

    async def find_similar_conditions(
        self,
        condition_text: str,
        n_results: int = 5
    ) -> List[SearchResult]:
        """Find similar conditions based on clinical description"""
        # Search both guidelines and ICD-10 codes
        guideline_results = await self.search_guidelines(condition_text, n_results=3)
        icd_results = await self.search_icd10(condition_text, n_results=n_results)

        # Combine and deduplicate
        combined = guideline_results + icd_results
        return sorted(combined, key=lambda x: x.score, reverse=True)[:n_results]

    def _format_results(self, results: dict) -> List[SearchResult]:
        """Format ChromaDB results into SearchResult objects"""
        formatted = []

        if not results or not results.get("ids"):
            return formatted

        ids = results["ids"][0] if results["ids"] else []
        documents = results["documents"][0] if results.get("documents") else []
        metadatas = results["metadatas"][0] if results.get("metadatas") else []
        distances = results["distances"][0] if results.get("distances") else []

        for i, doc_id in enumerate(ids):
            # Convert distance to similarity score (cosine distance to similarity)
            distance = distances[i] if i < len(distances) else 0
            score = 1 - distance  # Higher is better

            formatted.append(SearchResult(
                id=doc_id,
                content=documents[i] if i < len(documents) else "",
                metadata=metadatas[i] if i < len(metadatas) else {},
                score=score
            ))

        return formatted

    async def get_collection_stats(self) -> Dict[str, int]:
        """Get statistics about indexed collections"""
        self._lazy_init()

        stats = {}
        for collection_name in ["clinical_guidelines", "drug_database", "icd10_codes"]:
            try:
                collection = self._client.get_collection(collection_name)
                stats[collection_name] = collection.count()
            except Exception:
                stats[collection_name] = 0

        return stats


# Singleton instance
clinical_embeddings = ClinicalEmbeddings()


# Seed data loader
async def seed_knowledge_base():
    """Seed the ChromaDB with initial clinical knowledge"""
    from mcp_rag_server import CLINICAL_GUIDELINES, ICD10_DATABASE

    # Convert guidelines to list format
    guidelines = []
    for condition, data in CLINICAL_GUIDELINES.items():
        guidelines.append({
            "id": condition,
            "condition": condition,
            "title": data["title"],
            "content": data["content"],
            "icd10": data["icd10"],
            "cpt_codes": data["cpt_codes"],
            "source": data["source"]
        })

    # Add guidelines
    count = await clinical_embeddings.add_guidelines(guidelines)
    logger.info(f"Seeded {count} clinical guidelines")

    # Convert ICD-10 codes
    icd_codes = []
    for code, info in ICD10_DATABASE.items():
        icd_codes.append({
            "code": code,
            "description": info["description"],
            "category": info["category"]
        })

    # Add ICD-10 codes
    count = await clinical_embeddings.add_icd10_codes(icd_codes)
    logger.info(f"Seeded {count} ICD-10 codes")

    return {"guidelines": len(guidelines), "icd10_codes": len(icd_codes)}
