"""MCP HTTP endpoint views."""
import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .protocol import mcp_server

logger = logging.getLogger('mcp')


@csrf_exempt
@require_http_methods(["GET"])
def list_tools(request):
    return JsonResponse({"tools": mcp_server.list_tools()})


@csrf_exempt
@require_http_methods(["GET"])
def list_resources(request):
    return JsonResponse({"resources": mcp_server.list_resources()})


@csrf_exempt
@require_http_methods(["POST"])
def create_session(request):
    session_id = mcp_server.create_session()
    return JsonResponse({"session_id": session_id})


@csrf_exempt
@require_http_methods(["POST"])
def invoke_tool(request):
    try:
        body = json.loads(request.body)
        session_id = body.get("session_id", "")
        tool_name = body.get("tool_name")
        arguments = body.get("arguments", {})
        
        if not tool_name:
            return JsonResponse({"error": "tool_name required"}, status=400)
        
        result = mcp_server.invoke_tool(session_id, tool_name, arguments)
        return JsonResponse(result)
    except Exception as e:
        logger.error(f"MCP invoke error: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def read_resource(request):
    try:
        body = json.loads(request.body)
        uri = body.get("uri")
        params = body.get("params", {})
        
        if not uri:
            return JsonResponse({"error": "uri required"}, status=400)
        
        result = mcp_server.read_resource(uri, params)
        return JsonResponse(result)
    except Exception as e:
        logger.error(f"MCP read error: {e}")
        return JsonResponse({"error": str(e)}, status=500)
