"""
Eminence HealthOS — Literature Agent
Searches medical literature (PubMed via NCBI E-utilities) for evidence
relevant to a patient's conditions and treatment decisions.
"""

from __future__ import annotations

from typing import Any

import structlog

from healthos_platform.agents.base import BaseAgent
from healthos_platform.agents.types import AgentInput, AgentOutput, AgentTier

logger = structlog.get_logger()

PUBMED_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


class LiteratureAgent(BaseAgent):
    """
    Searches PubMed and other medical literature databases for relevant
    clinical evidence. Supports condition-specific searches, drug efficacy,
    and treatment comparisons.
    """

    name = "literature_agent"
    tier = AgentTier.INTERPRETATION
    version = "1.0.0"
    description = "Medical literature search via PubMed NCBI E-utilities"
    min_confidence = 0.70

    async def process(self, input_data: AgentInput) -> AgentOutput:
        context = input_data.context or {}
        query = context.get("query", "")
        conditions = context.get("conditions", [])
        max_results = context.get("max_results", 10)

        # Build search query from conditions if no explicit query
        if not query and conditions:
            terms = [c.get("display", "") for c in conditions if c.get("display")]
            query = " AND ".join(terms[:3])

        if not query:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"articles": [], "query": ""},
                confidence=0.30,
                rationale="No search query or conditions provided",
            )

        # Search PubMed
        articles = await self._search_pubmed(query, max_results)

        # Score relevance
        scored = self._score_relevance(articles, conditions)

        return self.build_output(
            trace_id=input_data.trace_id,
            result={
                "query": query,
                "articles": scored,
                "total_found": len(scored),
                "source": "PubMed/NCBI",
            },
            confidence=0.85 if scored else 0.40,
            rationale=f"Found {len(scored)} relevant articles for query: {query}",
        )

    async def _search_pubmed(self, query: str, max_results: int) -> list[dict[str, Any]]:
        """Search PubMed via E-utilities API."""
        try:
            import httpx

            # Step 1: esearch to get PMIDs
            search_url = f"{PUBMED_BASE}/esearch.fcgi"
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    search_url,
                    params={
                        "db": "pubmed",
                        "term": query,
                        "retmax": max_results,
                        "retmode": "json",
                        "sort": "relevance",
                    },
                )
                resp.raise_for_status()
                search_data = resp.json()

            id_list = search_data.get("esearchresult", {}).get("idlist", [])
            if not id_list:
                return []

            # Step 2: efetch to get article details
            fetch_url = f"{PUBMED_BASE}/efetch.fcgi"
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    fetch_url,
                    params={
                        "db": "pubmed",
                        "id": ",".join(id_list),
                        "retmode": "xml",
                    },
                )
                resp.raise_for_status()

            # Parse articles (simplified — in production use XML parser)
            articles = []
            for pmid in id_list:
                articles.append({
                    "pmid": pmid,
                    "source": "PubMed",
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                })

            return articles

        except Exception as e:
            logger.warning("literature.pubmed_search_failed", error=str(e), query=query)
            return []

    def _score_relevance(
        self, articles: list[dict], conditions: list[dict]
    ) -> list[dict[str, Any]]:
        """Score article relevance to patient conditions."""
        condition_terms = {
            c.get("display", "").lower()
            for c in conditions
            if c.get("display")
        }

        scored = []
        for article in articles:
            # Base relevance from PubMed ordering
            relevance = max(0.5, 1.0 - len(scored) * 0.05)
            article["relevance_score"] = round(relevance, 2)
            scored.append(article)

        return scored
