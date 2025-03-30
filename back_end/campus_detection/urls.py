from django.urls import path, include
from rest_framework.routers import DefaultRouter
from webapi.views import (
    CustomUserViewSet,
    HardwareNodeViewSet,
    ProcessTerminalViewSet,
    BuildingViewSet,
    AreaViewSet,
    HistoricalDataViewSet,
    DataUploadView,
    SummaryView
)

router = DefaultRouter()
router.register(r'users', CustomUserViewSet)
router.register(r'nodes', HardwareNodeViewSet)
router.register(r'terminals', ProcessTerminalViewSet)
router.register(r'buildings', BuildingViewSet)
router.register(r'areas', AreaViewSet)
router.register(r'historical', HistoricalDataViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
    path('api/upload/', DataUploadView.as_view()),
    path('api/summary/', SummaryView.as_view())
]