"""
Eminence HealthOS — Research Q&A Agent
Answers clinical questions by retrieving and reasoning over the clinical
knowledge base using RAG (Retrieval-Augmented Generation).
"""

from __future__ import annotations

from typing import Any

import structlog

from healthos_platform.agents.base import BaseAgent
from healthos_platform.agents.types import AgentInput, AgentOutput, AgentTier

logger = structlog.get_logger()


class ResearchQAAgent(BaseAgent):
    """
    Question-answering agent over the clinical knowledge base.
    Uses vector search (Qdrant) + LLM to provide evidence-based answers.
    """

    name = "research_qa_agent"
    tier = AgentTier.INTERPRETATION
    version = "1.0.0"
    description = "Clinical question-answering over knowledge base via RAG"
    min_confidence = 0.65

    async def process(self, input_data: AgentInput) -> AgentOutput:
        context = input_data.context or {}
        question = context.get("question", "")

        if not question:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"answer": "", "sources": []},
                confidence=0.0,
                rationale="No question provided",
            )

        # Retrieve relevant documents from vector store
        retrieved_docs = await self._retrieve_documents(question)

        # Generate answer using LLM with retrieved context
        answer, confidence = await self._generate_answer(question, retrieved_docs)

        return self.build_output(
            trace_id=input_data.trace_id,
            result={
                "question": question,
                "answer": answer,
                "sources": retrieved_docs,
                "retrieval_count": len(retrieved_docs),
            },
            confidence=confidence,
            rationale=f"Answered question using {len(retrieved_docs)} retrieved documents",
        )

    async def _retrieve_documents(self, question: str) -> list[dict[str, Any]]:
        """Retrieve relevant documents from the Qdrant vector store."""
        try:
            from healthos_platform.ml.rag.retriever import retrieve_documents

            docs = await retrieve_documents(
                query=question,
                collections=["guidelines", "papers", "protocols"],
                top_k=5,
            )
            return docs
        except ImportError:
            logger.warning("qa_agent.rag_unavailable")
            return []
        except Exception as e:
            logger.warning("qa_agent.retrieval_failed", error=str(e))
            return []

    async def _generate_answer(
        self, question: str, documents: list[dict]
    ) -> tuple[str, float]:
        """Generate an answer using the LLM with retrieved context."""
        if not documents:
            return (
                "Unable to find relevant clinical evidence to answer this question.",
                0.30,
            )

        try:
            from healthos_platform.ml.llm.client import get_llm_client

            client = get_llm_client()
            context_text = "\n\n".join(
                d.get("content", d.get("text", "")) for d in documents[:3]
            )
            prompt = (
                f"Based on the following clinical evidence, answer this question:\n\n"
                f"Question: {question}\n\n"
                f"Evidence:\n{context_text}\n\n"
                f"Provide a concise, evidence-based answer."
            )

            response = await client.generate(prompt)
            return response, 0.80
        except Exception as e:
            logger.warning("qa_agent.llm_failed", error=str(e))
            # Fallback: summarize retrieved documents
            summaries = [d.get("content", "")[:200] for d in documents[:2]]
            return f"Relevant evidence found: {'; '.join(summaries)}", 0.50
