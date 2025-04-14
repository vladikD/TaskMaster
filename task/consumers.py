from channels.generic.websocket import JsonWebsocketConsumer
from asgiref.sync import async_to_sync
from django.core.exceptions import ObjectDoesNotExist
from task.models import Project, Task, Column
from task.serializers import TaskNestedSerializer, ColumnSerializer

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
            message_type = "task_update"

        elif action == "move_column":
            column_id = content.get('column_id')
            new_order = int(content.get('new_order', 1))
            try:
                # Знаходимо колонку, яку переміщуємо.
                moved_column = Column.objects.get(pk=column_id, project_id=self.project_id)

                # Отримуємо всі інші колонки проекту, за замовчуванням відсортовані за order та id.
                other_columns = list(
                    Column.objects.filter(project_id=self.project_id).exclude(pk=column_id).order_by('order', 'id'))

                # Коригуємо new_order, щоб воно було в діапазоні 1 .. (кількість колон + 1)
                if new_order < 1:
                    new_order = 1
                elif new_order > len(other_columns) + 1:
                    new_order = len(other_columns) + 1

                # Вставляємо переміщувану колонку у список у потрібну позицію
                # Наприклад, якщо new_order==1, колонку вставляємо на початок списку.
                new_columns = other_columns[:new_order - 1] + [moved_column] + other_columns[new_order - 1:]

                # Перенумеровуємо колонки: призначаємо послідовні значення order, починаючи з 1.
                for idx, col in enumerate(new_columns, start=1):
                    if col.order != idx:
                        col.order = idx
                        col.save()

                # Формуємо відповідь з оновленим списком колон
                response = {
                    "action": "column_moved",
                    "columns": [ColumnSerializer(col).data for col in new_columns]
                }
            except Column.DoesNotExist:
                response = {"error": "Column not found or not part of this project"}
            message_type = "column_update"


        elif action == "add_column":
            # Реалізація додавання нової колонки через WebSocket
            column_name = content.get('column_name')
            try:
                # 'order' можна передавати як опціональний параметр; якщо не передано, за замовчуванням встановлюємо 0
                order = content.get('order', 0)
                # Створюємо колонку для проекту, до якого підключено WebSocket
                column = Column.objects.create(
                    project_id=self.project_id,
                    name=column_name,
                    order=order
                )
                response = {
                    "action": "column_added",
                    "column": {
                        "id": column.id,
                        "name": column.name,
                        "order": column.order,
                    }
                }
            except Exception as e:
                response = {"error": str(e)}
            message_type = "column_update"

        else:
            response = content
            message_type = "task_update"  # За замовчуванням або можна визначити інший тип

        async_to_sync(self.channel_layer.group_send)(
            self.group_name,
            {
                "type": message_type,
                "message": response,
            }
        )

    def task_update(self, event):
        self.send_json(event['message'])

    def column_update(self, event):
        self.send_json(event['message'])

    def comment_update(self, event):
        self.send_json(event['message'])
