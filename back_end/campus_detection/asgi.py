import os
import django
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.urls import path

# 导入WebSocket消费者
from webapi.consumers import TerminalConsumer

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'campus_detection.settings')
django.setup()  # 显式调用django.setup()

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
