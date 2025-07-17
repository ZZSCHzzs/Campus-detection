"""
ASGI config for campus_detection project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.urls import path

# 导入WebSocket消费者
from webapi.consumers import TerminalConsumer

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'campus_detection.settings')

# 定义WebSocket路由
websocket_urlpatterns = [
    path('ws/terminal/<int:terminal_id>/', TerminalConsumer.as_asgi()),
]

# 配置ASGI应用
application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            websocket_urlpatterns
        )
    ),
})
