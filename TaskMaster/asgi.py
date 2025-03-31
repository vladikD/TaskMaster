import os

# Встановлюємо змінну оточення до імпорту будь-яких модулів, які потребують налаштувань
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'TaskMaster.settings')

import django
django.setup()

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import task.routing

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            task.routing.websocket_urlpatterns
        )
    ),
})
