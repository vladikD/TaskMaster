from django.shortcuts import render
from rest_framework import viewsets, status, generics
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.mail import send_mail

from TaskMaster import settings
from .models import Task, Label, Project, Comment, Column, Invitation
from .permissions import IsMemberOfProject
from .serializers import TaskSerializer, LabelSerializer, ProjectSerializer, CommentSerializer, UserSerializer, \
    TokenObtainPairSerializer, ColumnSerializer, TaskNestedSerializer, ProjectNestedSerializer, CommentNestedSerializer, \
    InvitationSerializer
from django.contrib.auth.models import User
from django_filters.rest_framework import DjangoFilterBackend
import django_filters
from rest_framework import filters
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.utils import timezone
from django.shortcuts import redirect



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

    @action(detail=True, methods=['patch'], url_path='assign')
    def assign_user(self, request, pk=None):
        """
        Призначає користувача до задачі. URL: PATCH /api/tasks/<task_id>/assign/
        Очікуваний JSON:
        {
            "user_id": <ID користувача>
        }
        """
        task = self.get_object()
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({"error": "User id is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user_to_assign = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        # Перевірка: користувач повинен бути учасником цього проекту
        if not task.project.users.filter(pk=user_to_assign.pk).exists():
            return Response({"error": "User does not belong to the project."}, status=status.HTTP_400_BAD_REQUEST)

        task.assigned_to = user_to_assign
        task.save()

        # Надсилання push-оновлення через WebSocket (якщо потрібно)
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'project_{task.project.id}',
            {
                'type': 'task_update',
                'message': {
                    'action': 'user_assigned',
                    'task': TaskNestedSerializer(task).data,
                }
            }
        )

        return Response({"message": "User assigned to task successfully."}, status=status.HTTP_200_OK)


    @action(detail=True, methods=['delete'], url_path='unassign')
    def unassign(self, request, pk=None):
        """
        Видаляє користувача із задачі шляхом відміни призначення (assigned_to стає None).
        URL: DELETE /api/tasks/<task_id>/unassign/
        """
        task = self.get_object()
        # Переконаємося, що поточний користувач має доступ до цієї задачі
        if not task.project.users.filter(id=request.user.id).exists():
            raise PermissionDenied("У вас немає доступу до цього проєкту.")

        task.assigned_to = None
        task.save()

        # Надсилання push-повідомлення через WebSocket про зміну завдання
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'project_{task.project.id}',
            {
                'type': 'task_update',
                'message': {
                    'action': 'task_unassigned',
                    'task': TaskNestedSerializer(task).data,
                }
            }
        )
        return Response({"message": "User unassigned from task."}, status=status.HTTP_200_OK)
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

    @action(detail=True, methods=['post'], url_path='add-user')
    def add_user(self, request, pk=None):
        """
        Додає користувача до проекту.
        Очікуваний JSON-телo:
        {
           "user_id": <ID користувача>
        }
        URL: POST /api/projects/<project_id>/add-user/
        """
        project = self.get_object()
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({"error": "User ID is required."},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            user_to_add = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({"error": "User not found."},
                            status=status.HTTP_404_NOT_FOUND)

        # Перевірка: якщо користувач вже доданий, можна повернути відповідь
        if project.users.filter(pk=user_to_add.pk).exists():
            return Response({"message": f"User {user_to_add.username} is already added."},
                            status=status.HTTP_200_OK)

        # Додаємо користувача до проекту
        project.users.add(user_to_add)
        return Response({"message": f"User {user_to_add.username} added to project."},
                        status=status.HTTP_200_OK)

    @action(detail=True, methods=['delete'], url_path='remove-user/(?P<user_id>[^/.]+)')
    def remove_user(self, request, pk=None, user_id=None):
        print(f"Видаляємо користувача {user_id} з проекту {pk}")
        project = self.get_object()
        try:
            user_to_remove = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        project.users.remove(user_to_remove)
        tasks_to_update = project.tasks.filter(assigned_to=user_to_remove)
        for task in tasks_to_update:
            task.assigned_to = None
            task.save()

        return Response({"message": f"User {user_to_remove.username} removed from project and unassigned from tasks."},
                        status=status.HTTP_200_OK)


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


class InvitationCreateView(generics.CreateAPIView):
    serializer_class = InvitationSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        project_id = request.data.get('project')
        try:
            project = Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            return Response({"error": "Project not found."}, status=status.HTTP_404_NOT_FOUND)


        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            invitation = serializer.save()
            # Формуємо URL для прийняття запрошення
            accept_url = f"{request.scheme}://{request.get_host()}/invitations/accept/?token={invitation.token}"
            send_mail(
                subject=f"Запрошення до проекту {project.name}",
                message=f"Вас запрошують приєднатися до проекту {project.name}.\n Прийміть запрошення за посиланням: {accept_url}.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[invitation.email],
                fail_silently=False,
            )
            return Response({
                "message": "Invitation created and email sent successfully.",
                "token": invitation.token
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class InvitationAcceptView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        token = request.query_params.get('token')
        if not token:
            return Response({"error": "Token is required."}, status=400)
        try:
            invitation = Invitation.objects.get(token=token, accepted=False)
        except Invitation.DoesNotExist:
            return Response({"error": "Invalid or expired invitation token."}, status=400)

        if invitation.expires_at < timezone.now():
            return Response({"error": "Invitation token has expired."}, status=400)

        if request.user.is_authenticated:
            project = invitation.project
            project.users.add(request.user)
            invitation.accepted = True
            invitation.save()
            return Response({"message": "You have been added to the project."}, status=200)
        else:
            login_url = f"/login/?next=/invitations/accept/?token={token}"
            return redirect(login_url)