# task/tasks.py

from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from django.core.mail import send_mail
from django.conf import settings
from .models import Task

@shared_task
def send_deadline_reminders():
    """
    Знаходимо всі незавершені завдання, дедлайн яких – завтра,
    і висилаємо кожному відповідному користувачу email‑нагадування.
    """
    tomorrow = timezone.now().date() + timedelta(days=1)
    tasks = (
        Task.objects
            .filter(is_complete=False, due_date__date=tomorrow)
            .select_related('assigned_to', 'project')
    )

    for task in tasks:
        user = task.assigned_to
        if not user or not user.email:
            continue

        subject = f"Нагадування: дедлайн «{task.title}» завтра"
        message = (
            f"Привіт, {user.username}!\n\n"
            f"Нагадуємо, що дедлайн вашої задачі «{task.title}»\n"
            f"у проекті «{task.project.name}» – {tomorrow}.\n\n"
            "Перевірте статус задачі в системі: http://127.0.0.1:8000/project/"
            f"{task.project.id}/full/\n\n"
            "Успіхів!"
        )

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
