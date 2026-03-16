from django.urls import path
from . import views

urlpatterns = [
    path('agents/', views.list_agents, name='a2a-list-agents'),
    path('agents/<str:agent_id>/', views.get_agent, name='a2a-get-agent'),
    path('tasks/', views.list_tasks, name='a2a-list-tasks'),
    path('tasks/create/', views.create_task, name='a2a-create-task'),
    path('tasks/<str:task_id>/', views.get_task, name='a2a-get-task'),
    path('tasks/<str:task_id>/execute/', views.execute_task, name='a2a-execute-task'),
    path('orchestrate/', views.orchestrate_screening, name='a2a-orchestrate'),
]
