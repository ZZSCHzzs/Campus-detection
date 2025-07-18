import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'campus_detection.settings')
django.setup()  # 显式初始化Django

# 使用惰性加载，确保Django完全初始化后才导入消费者
application = None

def get_application():
    from channels.routing import ProtocolTypeRouter, URLRouter
    from channels.auth import AuthMiddlewareStack
    from django.urls import path
    from django.core.asgi import get_asgi_application
    
    # 导入消费者 - 在Django初始化后
    from webapi.consumers import TerminalConsumer

    websocket_urlpatterns = [
        # 同时添加带斜杠和不带斜杠的路由，但只接受整数ID
        path('ws/terminal/<int:terminal_id>/', TerminalConsumer.as_asgi()),
        path('ws/terminal/<int:terminal_id>', TerminalConsumer.as_asgi()),
    ]

    return ProtocolTypeRouter({
        "http": get_asgi_application(),
        "websocket": AuthMiddlewareStack(
            URLRouter(websocket_urlpatterns)
        ),
    })

# 立即调用函数获取应用实例
application = get_application()
