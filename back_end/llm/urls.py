from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LLMAnalysisViewSet, AgentChatView

router = DefaultRouter()
router.register(r'analysis', LLMAnalysisViewSet, basename='llmanalysis')

urlpatterns = [
    path('', include(router.urls)),
    path('chat/', AgentChatView.as_view(), name='agent-chat'),
]