from django.contrib import admin
from .models import Task, Label, Project, Comment

# Register your models here.
admin.site.register(Task)
admin.site.register(Label)
admin.site.register(Project)
admin.site.register(Comment)


