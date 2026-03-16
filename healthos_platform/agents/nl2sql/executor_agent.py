"""
Executor Agent

Safely executes SQL queries and formats results with PHI masking.
"""

import json
from typing import Dict, Any, List
import asyncpg

from ..security.phi_filter import PHIMasker, MaskingLevel


class ExecutorAgent:
    """Agent for executing SQL queries safely with PHI protection."""

    def __init__(
        self, database_url: str, masking_level: MaskingLevel = MaskingLevel.PARTIAL
    ):
        self.database_url = database_url
        self.masker = PHIMasker(default_level=masking_level)
        self.masking_enabled = True

    async def execute(
        self,
        sql: str,
        mask_phi: bool = True,
        masking_level: MaskingLevel = None,
    ) -> Dict[str, Any]:
        """
        Execute SQL query and return results with PHI masked.

        Returns dict with: data, row_count, phi_masked, error.
        """
        try:
            conn = await asyncpg.connect(self.database_url)

            statements = [s.strip() for s in sql.split(";") if s.strip()]
            results = []

            for stmt in statements:
                if not stmt:
                    continue

                is_select = stmt.strip().upper().startswith("SELECT")

                if is_select:
                    rows = await conn.fetch(stmt)
                    raw_rows = [dict(row) for row in rows]

                    if mask_phi and self.masking_enabled:
                        masked_rows = self.masker.mask_rows(raw_rows, masking_level)
                    else:
                        masked_rows = raw_rows

                    results.append({
                        "type": "SELECT",
                        "rows": masked_rows,
                        "count": len(rows),
                        "phi_masked": mask_phi and self.masking_enabled,
                    })
                else:
                    status = await conn.execute(stmt)
                    results.append({
                        "type": "EXECUTE",
                        "status": status,
                        "phi_masked": False,
                    })

            await conn.close()

            if len(results) == 1:
                result = results[0]
                if result["type"] == "SELECT":
                    return {
                        "data": self._format_rows(result["rows"]),
                        "row_count": result["count"],
                        "phi_masked": result["phi_masked"],
                    }
                else:
                    return {
                        "data": result["status"],
                        "row_count": 0,
                        "phi_masked": False,
                    }
            else:
                return {
                    "data": f"Executed {len(statements)} statements successfully",
                    "row_count": sum(
                        r.get("count", 0) for r in results if r["type"] == "SELECT"
                    ),
                    "phi_masked": any(r.get("phi_masked", False) for r in results),
                }

        except Exception as e:
            return {
                "error": str(e),
                "data": None,
                "row_count": 0,
                "phi_masked": False,
            }

    def _format_rows(self, rows: List[Dict]) -> str:
        """Format rows for display (PHI already masked)."""
        if not rows:
            return "No results found"

        if len(rows) == 1:
            return json.dumps(rows[0], default=str, indent=2)

        formatted = []
        display_limit = 20

        for i, row in enumerate(rows[:display_limit]):
            formatted.append(f"Record {i + 1}: {json.dumps(row, default=str)}")

        result = "\n".join(formatted)
        if len(rows) > display_limit:
            result += f"\n... and {len(rows) - display_limit} more records"

        return result

    def set_masking_enabled(self, enabled: bool):
        """Enable or disable PHI masking (for admin/debugging only)."""
        self.masking_enabled = enabled

    def set_masking_level(self, level: MaskingLevel):
        """Set default masking level."""
        self.masker.default_level = level

    async def validate_before_execute(self, sql: str) -> Dict[str, Any]:
        """Final validation before execution."""
        upper_sql = sql.upper()
        dangerous = ["DROP", "TRUNCATE", "ALTER TABLE", "CREATE DATABASE"]
        for keyword in dangerous:
            if keyword in upper_sql:
                return {"valid": False, "error": f"Blocked: {keyword} not allowed"}
        return {"valid": True}

    async def execute_with_audit(
        self,
        sql: str,
        session_id: str,
        user_id: str,
        mask_phi: bool = True,
    ) -> Dict[str, Any]:
        """Execute with additional audit information."""
        result = await self.execute(sql, mask_phi=mask_phi)

        result["audit"] = {
            "session_id": session_id,
            "user_id": user_id,
            "sql_hash": hash(sql),
            "phi_masked": result.get("phi_masked", False),
            "row_count": result.get("row_count", 0),
        }

        return result
