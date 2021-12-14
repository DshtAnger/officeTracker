# coding=utf-8
import json
from channels.generic.websocket import AsyncWebsocketConsumer

class UserConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user_id = self.scope['url_route']['kwargs']['user_id']
        self.user_id_group = 'messagePUSH_%s' % self.user_id

        # Join room group
        await self.channel_layer.group_add(
            self.user_id_group,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.user_id_group,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)

        # Send message to room group
        await self.channel_layer.group_send(
            self.user_id_group,
            {
                'type': 'push_message',
                'data': text_data_json
            }
        )

    # Receive message from room group
    async def push_message(self, event):
        data = event['data']

        # Send message to WebSocket
        await self.send( text_data=json.dumps(data) )