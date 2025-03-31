from channels.generic.websocket import JsonWebsocketConsumer
from asgiref.sync import async_to_sync
from django.core.exceptions import ObjectDoesNotExist
from task.models import Project, Task  # імпортуємо також Task для оновлення

class ProjectConsumer(JsonWebsocketConsumer):
    def connect(self):
        self.project_id = self.scope['url_route']['kwargs']['project_id']
        try:
            # Перевіряємо, чи існує проект із заданим ID
            project = Project.objects.get(pk=self.project_id)
        except Project.DoesNotExist:
            self.close(code=4001)
            return

        self.group_name = f'project_{self.project_id}'

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
        # Приклад: якщо повідомлення має дію "move_task"
        action = content.get('action')
        if action == "move_task":
            task_id = content.get('task_id')
            new_column = content.get('new_column')
            try:
                task = Task.objects.get(pk=task_id, project_id=self.project_id)
                # Оновлюємо колонку задачі
                task.column_id = new_column
                task.save()
                # Підготовка відповіді для всіх клієнтів
                response = {
                    "action": "task_moved",
                    "task_id": task_id,
                    "new_column": new_column,
                }
            except Task.DoesNotExist:
                response = {"error": "Task not found or not part of this project"}
        else:
            # Якщо дія не розпізнана, просто передаємо повідомлення всім
            response = content

        # Розсилаємо повідомлення всім у групі
        async_to_sync(self.channel_layer.group_send)(
            self.group_name,
            {
                'type': 'task_update',
                'message': response,
            }
        )

    def task_update(self, event):
        # Надсилаємо повідомлення клієнтам
        self.send_json(event['message'])
