import os
import django
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.urls import path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'campus_detection.settings')
django.setup()  # 显式初始化Django

# 延迟导入，避免提前触发模型导入
def get_application():
    from webapi.consumers import TerminalConsumer

    websocket_urlpatterns = [
        path('ws/terminal/<int:terminal_id>/', TerminalConsumer.as_asgi()),
    ]

    return ProtocolTypeRouter({
        "http": get_asgi_application(),
        "websocket": AuthMiddlewareStack(
            URLRouter(websocket_urlpatterns)
        ),
    })

application = get_application()
