"""WebSocket consumers for real-time updates."""
import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)


class WorkflowConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_name = 'workflow_updates'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
    
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
    
    async def receive(self, text_data):
        data = json.loads(text_data)
        await self.channel_layer.group_send(
            self.group_name,
            {'type': 'workflow_update', 'data': data}
        )
    
    async def workflow_update(self, event):
        await self.send(text_data=json.dumps(event['data']))


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_name = 'notifications'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
    
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
    
    async def notification(self, event):
        await self.send(text_data=json.dumps(event['data']))
