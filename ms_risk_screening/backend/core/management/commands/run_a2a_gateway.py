"""Management command to run the A2A gateway server."""
import json
import asyncio
import logging
from django.core.management.base import BaseCommand
from aiohttp import web

logger = logging.getLogger('a2a')


class Command(BaseCommand):
    help = 'Run the A2A (Agent-to-Agent) gateway server'

    def add_arguments(self, parser):
        parser.add_argument('--host', default='0.0.0.0')
        parser.add_argument('--port', type=int, default=9100)

    def handle(self, *args, **options):
        host = options['host']
        port = options['port']
        self.stdout.write(f"Starting A2A gateway on {host}:{port}")
        asyncio.run(self.run_server(host, port))

    async def run_server(self, host, port):
        from a2a.protocol import a2a_gateway

        async def handle_list_agents(request):
            return web.json_response({"agents": a2a_gateway.list_agents()})

        async def handle_get_agent(request):
            agent_id = request.match_info['agent_id']
            agent = a2a_gateway.get_agent(agent_id)
            if not agent:
                return web.json_response({"error": "Not found"}, status=404)
            return web.json_response(agent)

        async def handle_create_task(request):
            body = await request.json()
            task = a2a_gateway.create_task(
                body.get("from_agent", "user"),
                body["to_agent"],
                body["action"],
                body.get("payload", {}),
            )
            return web.json_response(task.to_dict(), status=201)

        async def handle_execute_task(request):
            task_id = request.match_info['task_id']
            result = a2a_gateway.execute_task(task_id)
            return web.json_response(result)

        async def handle_get_task(request):
            task_id = request.match_info['task_id']
            task = a2a_gateway.get_task(task_id)
            if not task:
                return web.json_response({"error": "Not found"}, status=404)
            return web.json_response(task)

        async def handle_list_tasks(request):
            status_filter = request.query.get("status")
            return web.json_response({"tasks": a2a_gateway.list_tasks(status_filter)})

        async def handle_orchestrate(request):
            body = await request.json()
            result = a2a_gateway.orchestrate_screening(body.get("patient_id", ""))
            return web.json_response(result)

        async def handle_health(request):
            return web.json_response({"status": "healthy", "service": "a2a-gateway"})

        app = web.Application()
        app.router.add_get('/health', handle_health)
        app.router.add_get('/agents', handle_list_agents)
        app.router.add_get('/agents/{agent_id}', handle_get_agent)
        app.router.add_post('/tasks/create', handle_create_task)
        app.router.add_post('/tasks/{task_id}/execute', handle_execute_task)
        app.router.add_get('/tasks/{task_id}', handle_get_task)
        app.router.add_get('/tasks', handle_list_tasks)
        app.router.add_post('/orchestrate', handle_orchestrate)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host, port)
        await site.start()
        self.stdout.write(self.style.SUCCESS(f"A2A gateway running on {host}:{port}"))
        await asyncio.Event().wait()
