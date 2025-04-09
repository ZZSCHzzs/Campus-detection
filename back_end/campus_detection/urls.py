from django.urls import path, include
from rest_framework.routers import DefaultRouter
from webapi.views import *

router = DefaultRouter()
router.register(r'users', CustomUserViewSet)
router.register(r'nodes', HardwareNodeViewSet)
router.register(r'terminals', ProcessTerminalViewSet)
router.register(r'buildings', BuildingViewSet)
router.register(r'areas', AreaViewSet)
router.register(r'historical', HistoricalDataViewSet)
router.register(r'alerts', AlertViewSet)
router.register(r'notice', NoticeViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
    path('api/upload/', DataUploadView.as_view()),
    path('api/summary/', SummaryView.as_view()),
    path('api/alert/', AlertView.as_view()),
    path('auth/', include('djoser.urls.jwt')),
    path('auth/', include('djoser.urls'))
]