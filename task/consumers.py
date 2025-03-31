from channels.generic.websocket import JsonWebsocketConsumer
from asgiref.sync import async_to_sync
from django.core.exceptions import ObjectDoesNotExist
from task.models import Project  # або імпортуйте вашу модель проекту


class ProjectConsumer(JsonWebsocketConsumer):
    def connect(self):
        self.project_id = self.scope['url_route']['kwargs']['project_id']

        # Перевіряємо, чи існує проект із заданим ID
        try:
            project = Project.objects.get(pk=self.project_id)
        except Project.DoesNotExist:
            # Якщо проект не існує, закриваємо з'єднання з кодом (наприклад, 4001)
            self.close(code=4001)
            return

        self.group_name = f'project_{self.project_id}'

        # Додаємо з'єднання до групи
        async_to_sync(self.channel_layer.group_add)(
            self.group_name,
            self.channel_name
        )
        self.accept()

    def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            async_to_sync(self.channel_layer.group_discard)(
                self.group_name,
                self.channel_name
            )

    def receive_json(self, content, **kwargs):
        # Обробка отриманих повідомлень від клієнта
        async_to_sync(self.channel_layer.group_send)(
            self.group_name,
            {
                'type': 'task_update',
                'message': content
            }
        )

    def task_update(self, event):
        self.send_json(event['message'])
