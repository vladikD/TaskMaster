from channels.generic.websocket import JsonWebsocketConsumer
from asgiref.sync import async_to_sync


class ProjectConsumer(JsonWebsocketConsumer):
    def connect(self):
        self.project_id = self.scope['url_route']['kwargs']['project_id']
        self.group_name = f'project_{self.project_id}'

        # Додаємо з'єднання до групи
        async_to_sync(self.channel_layer.group_add)(
            self.group_name,
            self.channel_name
        )
        self.accept()

    def disconnect(self, close_code):
        # Видаляємо з'єднання з групи
        async_to_sync(self.channel_layer.group_discard)(
            self.group_name,
            self.channel_name
        )

    def receive_json(self, content, **kwargs):
        # Обробка отриманих повідомлень від клієнта
        # Наприклад, повідомлення про переміщення задачі
        async_to_sync(self.channel_layer.group_send)(
            self.group_name,
            {
                'type': 'task_update',
                'message': content
            }
        )

    def task_update(self, event):
        # Надсилаємо повідомлення всім підключеним клієнтам у групі
        self.send_json(event['message'])
