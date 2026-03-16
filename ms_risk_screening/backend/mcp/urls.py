from django.urls import path
from . import views

urlpatterns = [
    path('tools/', views.list_tools, name='mcp-list-tools'),
    path('resources/', views.list_resources, name='mcp-list-resources'),
    path('session/', views.create_session, name='mcp-create-session'),
    path('invoke/', views.invoke_tool, name='mcp-invoke-tool'),
    path('read/', views.read_resource, name='mcp-read-resource'),
]
