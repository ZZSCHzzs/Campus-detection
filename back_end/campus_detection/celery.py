import os
from celery import Celery

# 设置 Django 默认配置
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'campus_detection.settings')

# 创建 Celery 实例
app = Celery('campus_detection')

# 使用 Django 的设置配置 Celery
app.config_from_object('django.conf:settings', namespace='CELERY')

# 自动发现并注册来自所有已注册 Django 应用的任务
app.autodiscover_tasks()

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
