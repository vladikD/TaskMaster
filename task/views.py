from django.shortcuts import render
from rest_framework import viewsets, status, generics
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Task, Label, Project, Comment, Column
from .permissions import IsMemberOfProject
from .serializers import TaskSerializer, LabelSerializer, ProjectSerializer, CommentSerializer, UserSerializer, \
    TokenObtainPairSerializer, ColumnSerializer, TaskNestedSerializer, ProjectNestedSerializer, CommentNestedSerializer
from django.contrib.auth.models import User
from django_filters.rest_framework import DjangoFilterBackend
import django_filters
from rest_framework import filters
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


# Creating a register view
class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'User created successfully!'}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Creating a obtain token view
class ObtainTokenView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = TokenObtainPairSerializer(data=request.data)
        if serializer.is_valid():
            return Response(serializer.validated_data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Filter for TASK
class TaskFilter(django_filters.FilterSet):
    is_complete = django_filters.BooleanFilter(field_name='is_complete')
    due_date = django_filters.DateFilter(field_name='due_date', lookup_expr='exact')
    assigned_to = django_filters.NumberFilter(field_name='assigned_to')
    labels = django_filters.CharFilter(field_name='labels__name', lookup_expr='icontains')
    project = django_filters.NumberFilter(field_name='project', lookup_expr='exact')

    class Meta:
        model = Task
        fields = ['is_complete', 'due_date', 'assigned_to', 'labels', 'project']

# ViewSets for Task
class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    permission_classes = [IsMemberOfProject]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = TaskFilter
    ordering_fields = ['due_date', 'created_at']
    ordering = ['created_at']

    def get_queryset(self):
        user = self.request.user
        queryset = Task.objects.filter(project__users=user)
        project_id = self.request.query_params.get('project')
        column_id = self.request.query_params.get('column')
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        if column_id:
            queryset = queryset.filter(column_id=column_id)
        return queryset

    def perform_create(self, serializer):
        # Перевірка, чи поточний користувач має доступ до проекту
        project = serializer.validated_data.get('project')
        user = self.request.user
        if not project.users.filter(id=user.id).exists():
            raise PermissionDenied("У вас немає доступу до цього проєкту.")
        # Створення задачі
        task = serializer.save()
        # Надсилання повідомлення про створення задачі через WebSocket
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'project_{task.project.id}',
            {
                'type': 'task_update',
                'message': {
                    'action': 'task_created',
                    'task': TaskNestedSerializer(task).data
                }
            }
        )

    def perform_update(self, serializer):
        # Оновлення задачі
        task = serializer.save()
        # Перевірка доступу (за потреби, якщо get_queryset уже це робить, можна пропустити)
        if not task.project.users.filter(id=self.request.user.id).exists():
            raise PermissionDenied("У вас немає доступу до цього проєкту.")
        # Надсилання повідомлення про оновлення задачі
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'project_{task.project.id}',
            {
                'type': 'task_update',
                'message': {
                    'action': 'task_updated',
                    'task': TaskNestedSerializer(task).data
                }
            }
        )

    def perform_destroy(self, instance):
        # Перевірка доступу перед видаленням
        if not instance.project.users.filter(id=self.request.user.id).exists():
            raise PermissionDenied("У вас немає доступу до цього проєкту.")
        project_id = instance.project.id
        task_id = instance.id
        instance.delete()
        # Надсилання повідомлення про видалення задачі
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'project_{project_id}',
            {
                'type': 'task_update',
                'message': {
                    'action': 'task_deleted',
                    'task_id': task_id,
                }
            }
        )

# ViewSets for Label
class LabelViewSet(viewsets.ModelViewSet):
    queryset = Label.objects.all()
    serializer_class = LabelSerializer
    permission_classes = [IsMemberOfProject]

    def get_queryset(self):
        return Label.objects.filter(tasks__project__users=self.request.user).distinct()

# ViewSets for Project
class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [IsMemberOfProject]

    def get_queryset(self):
        user = self.request.user
        return Project.objects.filter(users=user)

    def perform_create(self, serializer):
        project = serializer.save()
        user = self.request.user
        project.users.add(user)

# ViewSets for Comment
class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [IsMemberOfProject]

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Comment.objects.none()
        return Comment.objects.filter(task__project__users=self.request.user)

    def perform_create(self, serializer):
        # Перевірка доступу: переконайтеся, що поточний користувач має доступ до задачі, до якої додається коментар
        task = serializer.validated_data.get('task')
        if not task.project.users.filter(id=self.request.user.id).exists():
            raise PermissionDenied("Ви не маєте доступу до цього проєкту.")
        # Автоматично додамо користувача як автора коментаря
        comment = serializer.save(user=self.request.user)

        # Надсилання повідомлення через WebSocket
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'project_{comment.task.project.id}',  # група для проекту
            {
                'type': 'comment_update',
                'message': {
                    'action': 'comment_created',
                    'comment': CommentNestedSerializer(comment).data,
                }
            }
        )

    def perform_update(self, serializer):
        comment = serializer.save()
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'project_{comment.task.project.id}',
            {
                'type': 'comment_update',
                'message': {
                    'action': 'comment_updated',
                    'comment': CommentNestedSerializer(comment).data,
                }
            }
        )

    def perform_destroy(self, instance):
        project_id = instance.task.project.id
        comment_id = instance.id
        instance.delete()
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'project_{project_id}',
            {
                'type': 'comment_update',
                'message': {
                    'action': 'comment_deleted',
                    'comment_id': comment_id,
                }
            }
        )


class ColumnViewSet(viewsets.ModelViewSet):
    queryset = Column.objects.all()
    serializer_class = ColumnSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Приклад: фільтрувати колонки для певного проєкту, якщо передається параметр
        project_id = self.request.query_params.get('project')
        if project_id:
            return Column.objects.filter(project_id=project_id).order_by('order')
        return super().get_queryset()


class ProjectDetailNestedView(generics.RetrieveAPIView):
    queryset = Project.objects.all()
    serializer_class = ProjectNestedSerializer
    permission_classes = [IsAuthenticated]

