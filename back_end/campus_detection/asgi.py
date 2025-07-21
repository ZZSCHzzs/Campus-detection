import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'campus_detection.settings')
django.setup()  # 显式初始化Django

# 使用惰性加载，确保Django完全初始化后才导入消费者
application = None

def get_application():
    from channels.routing import ProtocolTypeRouter, URLRouter
    from channels.auth import AuthMiddlewareStack
    from django.urls import path, re_path
    from django.core.asgi import get_asgi_application
    
    # 导入消费者 - 在Django初始化后
    from webapi.consumers import TerminalConsumer, SystemBroadcastConsumer

    websocket_urlpatterns = [
        # 使用更规范的路由格式，确保终端ID只接受整数
        path('ws/terminal/<int:terminal_id>/', TerminalConsumer.as_asgi()),
        path('ws/terminal/<int:terminal_id>', TerminalConsumer.as_asgi()),
        
        # 添加一个额外的通用WebSocket路径用于系统消息广播
        path('ws/system/', SystemBroadcastConsumer.as_asgi()),
    ]

    return ProtocolTypeRouter({
        "http": get_asgi_application(),
        "websocket": AuthMiddlewareStack(
            URLRouter(websocket_urlpatterns)
        ),
    })

# 立即调用函数获取应用实例
application = get_application()
