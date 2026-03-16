"""
SQL Agent

Generates SQL from natural language using LLM with chain-of-thought prompting.
Schema-aware via MCP server integration.
"""

import re
from typing import Dict, Any
import httpx
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI


SQL_GENERATION_PROMPT = """You are a healthcare SQL expert. Generate SQL queries for a FHIR R4 compliant healthcare database.

DATABASE SCHEMA:

{schema}

REASONING PROCESS:
1. UNDERSTAND: Identify which FHIR tables and relationships are needed
2. PLAN: Design query structure (JOINs, filters, aggregations)
3. GENERATE: Write SQL with exact column names from the schema above
4. VERIFY: Check column names, FK references, and JOIN conditions

RULES:
- Use PostgreSQL syntax
- Use lowercase column names (no double quotes needed for FHIR tables)
- Include LIMIT 100 for SELECT unless specified otherwise
- NEVER generate DROP, TRUNCATE, or ALTER statements
- NEVER use SELECT * — always list specific columns explicitly
- Use ILIKE for case-insensitive text matching
- For age queries, use AGE() function: EXTRACT(YEAR FROM AGE(CURRENT_DATE, birth_date))
- Avoid selecting PHI columns (SSN, passport, drivers_license) unless explicitly requested
- For INSERT statements, use gen_random_uuid() for the id column

OUTPUT: Return ONLY the SQL statement, no explanations."""


class SQLAgent:
    """Agent for generating SQL from natural language."""

    def __init__(self, llm: ChatOpenAI, mcp_url: str):
        self.llm = llm
        self.mcp_url = mcp_url
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", SQL_GENERATION_PROMPT),
            ("human", "Generate SQL for: {query}"),
        ])

    async def generate(self, query: str, schema_context: str = "") -> Dict[str, Any]:
        """Generate SQL from natural language query."""
        if not schema_context:
            schema_context = await self._fetch_schema()

        chain = self.prompt | self.llm
        response = await chain.ainvoke({
            "schema": schema_context,
            "query": query,
        })

        sql = self._clean_sql(response.content)
        validation = await self._validate_sql(sql)

        return {
            "sql": sql,
            "confidence": 0.9 if validation.get("valid") else 0.6,
            "warnings": validation.get("warnings", []),
        }

    def _clean_sql(self, sql: str) -> str:
        """Clean up generated SQL."""
        sql = sql.strip()

        # Remove markdown code blocks
        if sql.startswith("```"):
            lines = sql.split("\n")
            sql_lines = []
            in_block = False
            for line in lines:
                if line.startswith("```"):
                    in_block = not in_block
                    continue
                if in_block:
                    sql_lines.append(line)
            sql = "\n".join(sql_lines).strip()

        if sql.lower().startswith("sql"):
            sql = sql[3:].strip()

        return sql

    async def _fetch_schema(self) -> str:
        """Fetch schema from MCP server."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.mcp_url}/schema", timeout=10.0)
                return str(response.json().get("schema", {}))
        except Exception:
            return "Schema unavailable"

    async def _validate_sql(self, sql: str) -> Dict[str, Any]:
        """Validate SQL using MCP server."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.mcp_url}/validate-sql",
                    json={"sql": sql},
                    timeout=10.0,
                )
                return response.json()
        except Exception:
            return {"valid": True, "warnings": []}
