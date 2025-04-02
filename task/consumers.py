from channels.generic.websocket import JsonWebsocketConsumer
from asgiref.sync import async_to_sync
from django.core.exceptions import ObjectDoesNotExist
from task.models import Project, Task
from task.serializers import TaskNestedSerializer


class ProjectConsumer(JsonWebsocketConsumer):
    def connect(self):
        self.project_id = self.scope['url_route']['kwargs']['project_id']
        try:
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
        # Цей метод обробляє вхідні повідомлення від клієнтів, наприклад, для переміщення задач
        # Ми можемо використовувати його, якщо фронтенд надсилає повідомлення, яке потребує оновлення
        action = content.get('action')
        if action == "move_task":
            task_id = content.get('task_id')
            new_column = content.get('new_column')
            try:
                task = Task.objects.get(pk=task_id, project_id=self.project_id)
                task.column_id = new_column
                task.save()
                response = {
                    "action": "task_moved",
                    "task": TaskNestedSerializer(task).data,
                }
            except Task.DoesNotExist:
                response = {"error": "Task not found or not part of this project"}
        else:
            response = content

        async_to_sync(self.channel_layer.group_send)(
            self.group_name,
            {
                'type': 'task_update',
                'message': response,
            }
        )

    def task_update(self, event):
        self.send_json(event['message'])

    def comment_update(self, event):
        self.send_json(event['message'])

