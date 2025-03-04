# file: task/permissions.py

from rest_framework import permissions
from rest_framework.permissions import SAFE_METHODS
from .models import Task, Project, Comment

class IsMemberOfProject(permissions.BasePermission):
    """
    Дозволяє доступ, якщо:
      1) користувач - staff (адмін), або
      2) користувач є учасником того проекту, до якого належить об’єкт Task/Project/Comment.
    При цьому перевірка відбувається як на рівні списку (has_permission),
    так і на рівні конкретного об’єкта (has_object_permission).
    """

    def has_permission(self, request, view):
        # 1) Відмовляємо, якщо користувач не автентифікований
        if not request.user.is_authenticated:
            return False

        # 2) Якщо користувач - staff, дозволяємо все
        if request.user.is_staff:
            return True

        # 3) Якщо це безпечні методи (GET, HEAD, OPTIONS), дозволяємо,
        # але при цьому додатково фільтруємо об'єкти в get_queryset().
        # Наприклад, TaskViewSet.get_queryset(), ProjectViewSet.get_queryset(), і т.д.
        if request.method in SAFE_METHODS:
            return True

        # 4) Якщо метод не безпечний (POST, PUT, PATCH, DELETE),
        # усе одно пропускаємо, але перевірка буде на рівні об’єкта
        # (perform_create або has_object_permission).
        return True

    def has_object_permission(self, request, view, obj):
        # 1) Якщо користувач staff – дозволити все
        if request.user.is_staff:
            return True

        # 2) Якщо об’єкт - це Task, перевірити, чи користувач у project.users
        if isinstance(obj, Task):
            return obj.project.users.filter(id=request.user.id).exists()

        # 3) Якщо об’єкт - це Project, перевірити, чи користувач у цьому .users
        elif isinstance(obj, Project):
            return obj.users.filter(id=request.user.id).exists()

        # 4) Якщо об’єкт - це Comment, перевірити, чи користувач у project.users
        elif isinstance(obj, Comment):
            # Коментар належить завданню, а те – проекту
            return obj.task.project.users.filter(id=request.user.id).exists()

        # Якщо якийсь інший об’єкт — на всяк випадок заборонити
        return False
