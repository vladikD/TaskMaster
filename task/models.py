from django.db import models

# Create your models here.

from django.db import models
from django.contrib.auth.models import User

# Model for tasks
class Task(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    due_date = models.DateTimeField(null=True, blank=True)
    is_complete = models.BooleanField(default=False)
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    labels = models.ManyToManyField('Label', related_name='tasks', blank=True)

    class Meta:
        indexes = [
        models.Index(fields=['due_date']),
        models.Index(fields=['assigned_to']),
    ]

    def __str__(self):
        return self.title

# Model for labels
class Label(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name

# Models for Projects
class Project(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    users = models.ManyToManyField(User, related_name='projects')

    def __str__(self):
        return self.name

# Model for Comments
class Comment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user.username} on {self.task.title}'
