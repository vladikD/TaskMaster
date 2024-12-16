from rest_framework import permissions
from task.models import Task

# Adding access for project members
class IsMemberOfProject(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if isinstance(obj, Task):
            return obj.project.users.filter(id=request.user.id).exists()
        return False

# Adding access for admin users
class IsAdminUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_staff