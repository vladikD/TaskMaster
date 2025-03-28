from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Task, Label, Project, Comment
from .permissions import IsMemberOfProject
from .serializers import TaskSerializer, LabelSerializer, ProjectSerializer, CommentSerializer, UserSerializer, TokenObtainPairSerializer
from django.contrib.auth.models import User
from django_filters.rest_framework import DjangoFilterBackend
import django_filters
from rest_framework import filters


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
        return Task.objects.filter(project__users=user)

    def perform_create(self, serializer):
        project = serializer.validated_data.get('project')
        user = self.request.user
        if not project.users.filter(id=user.id).exists():
            raise PermissionDenied("У вас немає доступу до цього проєктую.")

        serializer.save()
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
        return Comment.objects.filter(task__project__users=self.request.user)

    def perform_create(self, serializer):
        task = serializer.validated_data.get('task')
        if not task.project.users.filter(id=self.request.user.id).exists():
            raise PermissionDenied("Ви не маєте доступу до завдань цього проєкту.")
        serializer.save()