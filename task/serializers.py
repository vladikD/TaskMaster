from django.contrib.auth import authenticate
from rest_framework import serializers
from .models import Task, Label, Project, Comment, Column
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken


class ColumnSerializer(serializers.ModelSerializer):
    class Meta:
        model = Column
        fields = ['id', 'name', 'project', 'order']


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model=User
        fields=['username','email', 'password']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user


class TokenObtainPairSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()

    def validate(self, attrs):
        user = authenticate(**attrs)
        if user is None:
            raise serializers.ValidationError('Invalid username or password')
        refresh = RefreshToken.for_user(user)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token)
        }

# Serializer for Tasks
class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ['id', 'title', 'description', 'created_at', 'due_date', 'is_complete',
                  'assigned_to', 'labels', 'project', 'column']

# Serializer for Labels
class LabelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Label
        fields = '__all__'

# Serializer for Projects
class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['id', 'name', 'description', 'users']

# Serializer for Comments
class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = '__all__'


class TaskNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ('id', 'title')


class ColumnNestedSerializer(serializers.ModelSerializer):
    tasks = TaskNestedSerializer(many=True, read_only=True)

    class Meta:
        model = Column
        fields = ('id', 'name', 'order', 'tasks')


class ProjectNestedSerializer(serializers.ModelSerializer):
    columns = ColumnNestedSerializer(many=True, read_only=True)

    class Meta:
        model = Project
        fields = ('id', 'name', 'description', 'columns')


