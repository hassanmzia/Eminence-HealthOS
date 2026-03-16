"""
Base MCP Server Implementation for Healthcare
Provides common functionality for all MCP servers
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, Optional
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Header, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
import logging
import time
import uuid
import os
from datetime import datetime
from functools import wraps

# Import auth and audit modules
# Support both package import and direct execution
try:
    from .auth import get_current_user, AuthenticatedUser, require_permission, REQUIRE_AUTH
    from .audit import audit_logger, log_mcp_tool_call, AuditEntry, AuditEventType, AuditSeverity
except ImportError:
    from auth import get_current_user, AuthenticatedUser, require_permission, REQUIRE_AUTH
    from audit import audit_logger, log_mcp_tool_call, AuditEntry, AuditEventType, AuditSeverity

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# MCP Protocol Types
# ============================================================================

class MCPToolDefinition(BaseModel):
    """Definition of an MCP tool"""
    name: str
    description: str
    input_schema: dict
    output_schema: dict
    category: str = "general"
    requires_patient_context: bool = True


class MCPRequest(BaseModel):
    """Standard MCP request format"""
    tool_name: str
    arguments: dict
    request_id: Optional[str] = None
    patient_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None

    def __init__(self, **data):
        if not data.get("request_id"):
            data["request_id"] = str(uuid.uuid4())
        super().__init__(**data)


class MCPResponse(BaseModel):
    """Standard MCP response format"""
    request_id: str
    tool_name: str
    success: bool
    data: Any = None
    error: Optional[str] = None
    metadata: dict = {}
    execution_time_ms: float = 0
    timestamp: Optional[str] = None

    def __init__(self, **data):
        if not data.get("timestamp"):
            data["timestamp"] = datetime.utcnow().isoformat()
        super().__init__(**data)


class AuditLogEntry(BaseModel):
    """HIPAA-compliant audit log entry"""
    timestamp: datetime
    request_id: str
    user_id: str
    patient_id: Optional[str] = None
    tool_name: str
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    success: bool
    error_message: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


# ============================================================================
# Base MCP Server
# ============================================================================

class BaseMCPServer(ABC):
    """
    Base class for all MCP servers in the healthcare platform.
    Provides common functionality like:
    - Tool registration
    - Authentication
    - Audit logging
    - Error handling
    - HIPAA compliance
    """

    def __init__(self, name: str, description: str, version: str = "1.0.0"):
        self.name = name
        self.description = description
        self.version = version
        self.tools: dict[str, Callable] = {}
        self.tool_definitions: dict[str, MCPToolDefinition] = {}
        self.app = self._create_app()
        self._register_routes()

    def _create_app(self) -> FastAPI:
        """Create FastAPI application with middleware"""
        app = FastAPI(
            title=f"MCP Server: {self.name}",
            description=self.description,
            version=self.version
        )

        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        return app

    def _register_routes(self):
        """Register standard MCP routes"""

        @self.app.get("/")
        async def root():
            return {
                "server": self.name,
                "description": self.description,
                "version": self.version,
                "tools_count": len(self.tools)
            }

        @self.app.get("/tools")
        async def list_tools():
            """List all available tools"""
            return {
                "tools": [
                    {
                        "name": name,
                        "description": defn.description,
                        "category": defn.category,
                        "requires_patient_context": defn.requires_patient_context
                    }
                    for name, defn in self.tool_definitions.items()
                ]
            }

        @self.app.get("/tools/{tool_name}/schema")
        async def get_tool_schema(tool_name: str):
            """Get schema for a specific tool"""
            if tool_name not in self.tool_definitions:
                raise HTTPException(status_code=404, detail=f"Tool {tool_name} not found")
            return self.tool_definitions[tool_name].dict()

        @self.app.post("/tools/{tool_name}")
        async def invoke_tool(
            tool_name: str,
            request: Request,
            authorization: str = Header(default=None),
            user: Optional[AuthenticatedUser] = Depends(get_current_user)
        ):
            """Invoke a tool with authentication and audit logging"""
            if tool_name not in self.tools:
                raise HTTPException(status_code=404, detail=f"Tool {tool_name} not found")

            start_time = time.time()
            body = await request.json()

            # Get user info from auth or request body
            user_id = user.user_id if user else body.get("user_id", "anonymous")

            # Get client IP
            client_ip = request.client.host if request.client else None
            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                client_ip = forwarded.split(",")[0].strip()

            mcp_request = MCPRequest(
                tool_name=tool_name,
                arguments=body.get("arguments", body),
                patient_id=body.get("patient_id"),
                user_id=user_id,
                session_id=body.get("session_id")
            )

            # Log tool invocation
            await log_mcp_tool_call(
                tool_name=tool_name,
                user_id=user_id,
                patient_id=mcp_request.patient_id,
                request_id=mcp_request.request_id,
                arguments=mcp_request.arguments,
                ip_address=client_ip
            )

            try:
                # Execute tool
                result = await self.tools[tool_name](mcp_request)
                execution_time = (time.time() - start_time) * 1000

                # Audit log success
                await self._audit_log(mcp_request, True, ip_address=client_ip)

                return MCPResponse(
                    request_id=mcp_request.request_id,
                    tool_name=tool_name,
                    success=True,
                    data=result,
                    execution_time_ms=execution_time
                )

            except Exception as e:
                logger.error(f"Tool {tool_name} failed: {str(e)}")
                await self._audit_log(mcp_request, False, str(e), ip_address=client_ip)

                return MCPResponse(
                    request_id=mcp_request.request_id,
                    tool_name=tool_name,
                    success=False,
                    error=str(e),
                    execution_time_ms=(time.time() - start_time) * 1000
                )

        @self.app.get("/health")
        async def health():
            return {"status": "healthy", "server": self.name}

    def register_tool(
        self,
        name: str,
        description: str,
        input_schema: dict,
        output_schema: dict,
        category: str = "general",
        requires_patient_context: bool = True
    ):
        """Decorator to register a tool"""
        def decorator(func: Callable):
            self.tool_definitions[name] = MCPToolDefinition(
                name=name,
                description=description,
                input_schema=input_schema,
                output_schema=output_schema,
                category=category,
                requires_patient_context=requires_patient_context
            )

            @wraps(func)
            async def wrapper(request: MCPRequest):
                return await func(request)

            self.tools[name] = wrapper
            return wrapper
        return decorator

    async def _audit_log(self, request: MCPRequest, success: bool, error: str = None, ip_address: str = None):
        """Log access for HIPAA compliance - persists to PostgreSQL"""
        entry = AuditEntry(
            event_type=AuditEventType.MCP_TOOL_SUCCESS if success else AuditEventType.MCP_TOOL_ERROR,
            timestamp=datetime.utcnow(),
            user_id=request.user_id or "system",
            action=f"mcp:{request.tool_name}",
            patient_id=request.patient_id,
            request_id=request.request_id,
            session_id=request.session_id,
            resource_type=self.name,
            resource_id=request.tool_name,
            success=success,
            severity=AuditSeverity.INFO if success else AuditSeverity.ERROR,
            error_message=error,
            ip_address=ip_address,
            phi_accessed=request.patient_id is not None
        )

        # Persist to database via audit logger
        await audit_logger.log(entry)

    @abstractmethod
    def setup_tools(self):
        """Override to register tools specific to this server"""
        pass
