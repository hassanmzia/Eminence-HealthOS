"""Management command to run the MCP server."""
import json
import asyncio
import logging
from django.core.management.base import BaseCommand
from aiohttp import web

logger = logging.getLogger('mcp')


class Command(BaseCommand):
    help = 'Run the MCP (Model Context Protocol) server'

    def add_arguments(self, parser):
        parser.add_argument('--host', default='0.0.0.0')
        parser.add_argument('--port', type=int, default=9000)

    def handle(self, *args, **options):
        host = options['host']
        port = options['port']
        self.stdout.write(f"Starting MCP server on {host}:{port}")
        asyncio.run(self.run_server(host, port))

    async def run_server(self, host, port):
        from mcp.protocol import mcp_server

        async def handle_list_tools(request):
            return web.json_response({"tools": mcp_server.list_tools()})

        async def handle_list_resources(request):
            return web.json_response({"resources": mcp_server.list_resources()})

        async def handle_create_session(request):
            session_id = mcp_server.create_session()
            return web.json_response({"session_id": session_id})

        async def handle_invoke(request):
            body = await request.json()
            result = mcp_server.invoke_tool(
                body.get("session_id", ""),
                body.get("tool_name", ""),
                body.get("arguments", {})
            )
            return web.json_response(result)

        async def handle_read(request):
            body = await request.json()
            result = mcp_server.read_resource(
                body.get("uri", ""),
                body.get("params", {})
            )
            return web.json_response(result)

        async def handle_health(request):
            return web.json_response({"status": "healthy", "service": "mcp-server"})

        app = web.Application()
        app.router.add_get('/health', handle_health)
        app.router.add_get('/tools', handle_list_tools)
        app.router.add_get('/resources', handle_list_resources)
        app.router.add_post('/session', handle_create_session)
        app.router.add_post('/invoke', handle_invoke)
        app.router.add_post('/read', handle_read)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host, port)
        await site.start()
        self.stdout.write(self.style.SUCCESS(f"MCP server running on {host}:{port}"))
        await asyncio.Event().wait()
