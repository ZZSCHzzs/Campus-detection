from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # 使用复数形式"terminals"
    re_path(r'ws/terminals/(?P<terminal_id>\d+)/$', consumers.TerminalConsumer.as_asgi()),
]
