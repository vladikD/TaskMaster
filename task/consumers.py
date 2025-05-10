from channels.generic.websocket import JsonWebsocketConsumer
from asgiref.sync import async_to_sync
from task.models import Project, Task, Column
from task.serializers import ColumnSerializer, TaskOrderSerializer

class ProjectConsumer(JsonWebsocketConsumer):
    def connect(self):
        self.project_id = self.scope['url_route']['kwargs']['project_id']
        try:
            Project.objects.get(pk=self.project_id)
        except Project.DoesNotExist:
            return self.close(code=4001)

        self.group_name = f'project_{self.project_id}'
        async_to_sync(self.channel_layer.group_add)(
            self.group_name,
            self.channel_name
        )
        self.accept()

    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)(
            self.group_name,
            self.channel_name
        )

    def receive_json(self, content, **kwargs):
        action = content.get('action')

        if action == "move_task":
            task_id    = content.get('task_id')
            to_column  = content.get('new_column')
            new_order  = int(content.get('new_order', 1))

            try:
                task = Task.objects.get(pk=task_id, project_id=self.project_id)
            except Task.DoesNotExist:
                return  # ігноруємо невірні запити

            from_column = task.column_id

            # 1) Переміщуємо таску (якщо змінилася колонка)
            task.column_id = to_column
            task.order     = new_order
            task.save(update_fields=['column_id','order'])

            # 2) Перенумеровуємо таски у старій колонці
            src_tasks_qs = Task.objects.filter(
                project_id=self.project_id,
                column_id=from_column
            ).order_by('order','id')
            src_tasks = list(src_tasks_qs)
            for idx, t in enumerate(src_tasks, start=1):
                if t.order != idx:
                    t.order = idx
                    t.save(update_fields=['order'])

            # 3) Перенумеровуємо таски у новій колонці
            tgt_tasks_qs = Task.objects.filter(
                project_id=self.project_id,
                column_id=to_column
            ).order_by('order','id')
            tgt_tasks = list(tgt_tasks_qs)
            for idx, t in enumerate(tgt_tasks, start=1):
                if t.order != idx:
                    t.order = idx
                    t.save(update_fields=['order'])

            # 4) Підготуємо payload
            response = {
                "action":       "task_moved",
                "task_id":      task_id,
                "from_column":  from_column,
                "to_column":    to_column,
                "source_tasks": TaskOrderSerializer(src_tasks, many=True).data,
                "target_tasks": TaskOrderSerializer(tgt_tasks, many=True).data,
            }
            message_type = "task_update"

        elif action == "move_column":
            column_id = content.get('column_id')
            new_order = int(content.get('new_order', 1))
            try:
                moved_column = Column.objects.get(
                    pk=column_id,
                    project_id=self.project_id
                )
            except Column.DoesNotExist:
                return

            other_columns = list(
                Column.objects.filter(
                    project_id=self.project_id
                ).exclude(pk=column_id).order_by('order','id')
            )

            # виправляємо межі
            new_order = max(1, min(new_order, len(other_columns) + 1))

            # Формуємо новий список і заново нумеруємо
            new_columns = (
                other_columns[:new_order-1]
                + [moved_column]
                + other_columns[new_order-1:]
            )
            for idx, col in enumerate(new_columns, start=1):
                if col.order != idx:
                    col.order = idx
                    col.save(update_fields=['order'])

            response = {
                "action":  "column_moved",
                "columns": [ColumnSerializer(col).data for col in new_columns],
            }
            message_type = "column_update"

        elif action == "add_column":
            column_name = content.get('column_name')
            order       = int(content.get('order', 0))
            column = Column.objects.create(
                project_id=self.project_id,
                name=column_name,
                order=order
            )
            response = {
                "action": "column_added",
                "column": ColumnSerializer(column).data
            }
            message_type = "column_update"

        else:
            # якщо інші дії — просто ехо
            response     = content
            message_type = "task_update"

        # Відправляємо всім клієнтам у групі
        async_to_sync(self.channel_layer.group_send)(
            self.group_name,
            {"type": message_type, "message": response}
        )

    # Обробники вхідних group_send
    def task_update(self, event):
        self.send_json(event['message'])

    def column_update(self, event):
        self.send_json(event['message'])

    def comment_update(self, event):
        self.send_json(event['message'])

    def project_update(self, event):
        self.send_json(event['message'])
