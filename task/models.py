import uuid
from datetime import timedelta

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


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


#Model for Tasks
class Task(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    due_date = models.DateTimeField(null=True, blank=True)
    is_complete = models.BooleanField(default=False)
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    labels = models.ManyToManyField('Label', related_name='tasks', blank=True)
    project = models.ForeignKey('Project', related_name='tasks', on_delete=models.CASCADE)
    column = models.ForeignKey("task.Column", on_delete=models.CASCADE, related_name='tasks')

    estimated_time = models.DurationField(
        null=True,
        blank=True,
        help_text="Очікувана тривалість завдання (наприклад, PT1H30M для 1 години 30 хвилин)"
    )
    time_spent = models.DurationField(
        default=timedelta(0),
        help_text="Фактично витрачений час"
    )

    class Meta:
        indexes = [
        models.Index(fields=['due_date']),
        models.Index(fields=['assigned_to']),
    ]

    def __str__(self):
        return self.title

# Model for Columns
class Column(models.Model):
    name = models.CharField(max_length=100)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='columns')
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.name} ({self.project.name})"
# Model for Comments
class Comment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user.username} on {self.task.title}'


class Invitation(models.Model):
    email = models.EmailField()
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='invitations')
    token = models.CharField(max_length=64, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    accepted = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = uuid.uuid4().hex
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=7)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Invitation for {self.email} to project {self.project.name}"