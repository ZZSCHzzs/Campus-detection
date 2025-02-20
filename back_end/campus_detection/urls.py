from django.urls import path, include
from rest_framework.routers import DefaultRouter
from webapi.views import (
    CustomUserViewSet,
    HardwareNodeViewSet,
    ProcessTerminalViewSet,
    BuildingViewSet,
    AreaViewSet,
    HistoricalDataViewSet,
    DataUploadView
)

router = DefaultRouter()
router.register(r'users', CustomUserViewSet)
router.register(r'hardware-nodes', HardwareNodeViewSet)
router.register(r'process-terminals', ProcessTerminalViewSet)
router.register(r'buildings', BuildingViewSet)
router.register(r'areas', AreaViewSet)
router.register(r'historical-data', HistoricalDataViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
    path('api/upload/', DataUploadView.as_view())
]