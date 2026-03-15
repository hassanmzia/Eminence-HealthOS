"""
Eminence HealthOS -- Agent Tool Library

LangChain-compatible tools for clinical AI agents. Each module exposes a
list of ``@tool``-decorated callables plus a convenience ``*_TOOLS`` list
for bulk registration.

All infrastructure configuration (database URLs, API keys, service
endpoints) is sourced from ``healthos_platform.config.settings`` via the
Pydantic ``Settings`` model, with no Django dependency.
"""

from tools.base_tools import ALL_BASE_TOOLS, TOOL_MAP  # noqa: F401
from tools.fhir_tools import FHIR_TOOLS  # noqa: F401
from tools.geospatial_tools import GEOSPATIAL_TOOLS  # noqa: F401
from tools.graph_tools import GRAPH_TOOLS  # noqa: F401
from tools.nl2sql_tool import NL2SQL_TOOLS  # noqa: F401
from tools.notification_tools import NOTIFICATION_TOOLS  # noqa: F401
from tools.vector_tools import VECTOR_TOOLS  # noqa: F401
from tools.voice_tool import VOICE_TOOLS  # noqa: F401

ALL_TOOLS: list = (
    ALL_BASE_TOOLS
    + FHIR_TOOLS
    + GEOSPATIAL_TOOLS
    + GRAPH_TOOLS
    + NL2SQL_TOOLS
    + NOTIFICATION_TOOLS
    + VECTOR_TOOLS
    + VOICE_TOOLS
)

__all__ = [
    "ALL_TOOLS",
    "TOOL_MAP",
    "ALL_BASE_TOOLS",
    "FHIR_TOOLS",
    "GEOSPATIAL_TOOLS",
    "GRAPH_TOOLS",
    "NL2SQL_TOOLS",
    "NOTIFICATION_TOOLS",
    "VECTOR_TOOLS",
    "VOICE_TOOLS",
]
