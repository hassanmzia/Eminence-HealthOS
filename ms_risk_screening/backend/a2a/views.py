"""A2A HTTP endpoint views."""
import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .protocol import a2a_gateway

logger = logging.getLogger('a2a')


@csrf_exempt
@require_http_methods(["GET"])
def list_agents(request):
    return JsonResponse({"agents": a2a_gateway.list_agents()})


@csrf_exempt
@require_http_methods(["GET"])
def get_agent(request, agent_id):
    agent = a2a_gateway.get_agent(agent_id)
    if not agent:
        return JsonResponse({"error": "Agent not found"}, status=404)
    return JsonResponse(agent)


@csrf_exempt
@require_http_methods(["POST"])
def create_task(request):
    try:
        body = json.loads(request.body)
        task = a2a_gateway.create_task(
            from_agent=body.get("from_agent", "user"),
            to_agent=body["to_agent"],
            action=body["action"],
            payload=body.get("payload", {}),
        )
        return JsonResponse(task.to_dict(), status=201)
    except KeyError as e:
        return JsonResponse({"error": f"Missing field: {e}"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def execute_task(request, task_id):
    result = a2a_gateway.execute_task(task_id)
    return JsonResponse(result)


@csrf_exempt
@require_http_methods(["GET"])
def get_task(request, task_id):
    task = a2a_gateway.get_task(task_id)
    if not task:
        return JsonResponse({"error": "Task not found"}, status=404)
    return JsonResponse(task)


@csrf_exempt
@require_http_methods(["GET"])
def list_tasks(request):
    status_filter = request.GET.get("status")
    return JsonResponse({"tasks": a2a_gateway.list_tasks(status_filter)})


@csrf_exempt
@require_http_methods(["POST"])
def orchestrate_screening(request):
    try:
        body = json.loads(request.body)
        patient_id = body.get("patient_id")
        if not patient_id:
            return JsonResponse({"error": "patient_id required"}, status=400)
        result = a2a_gateway.orchestrate_screening(patient_id)
        return JsonResponse(result)
    except Exception as e:
        logger.error(f"A2A orchestration error: {e}")
        return JsonResponse({"error": str(e)}, status=500)
