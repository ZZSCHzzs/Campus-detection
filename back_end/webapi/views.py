from rest_framework import viewsets
from rest_framework.decorators import action, permission_classes
from rest_framework.views import APIView
from .models import *
from .serializers import *
from rest_framework.response import Response
from rest_framework import status


def get_summary_people_count():
    # 获取所有区域
    areas = Area.objects.all()
    people_count = 0
    for area in areas:
        people_count += area.bound_node.detected_count
    return people_count


class CustomUserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer


class HardwareNodeViewSet(viewsets.ModelViewSet):
    queryset = HardwareNode.objects.all()
    serializer_class = HardwareNodeSerializer


class ProcessTerminalViewSet(viewsets.ModelViewSet):
    queryset = ProcessTerminal.objects.all()
    serializer_class = ProcessTerminalSerializer

    @action(detail=True, methods=['get'])
    def nodes(self, request, pk=None):
        terminal = self.get_object()
        nodes = HardwareNode.objects.filter(terminal=terminal)
        serializer = HardwareNodeSerializer(nodes, many=True)
        return Response(serializer.data)


class BuildingViewSet(viewsets.ModelViewSet):
    queryset = Building.objects.all()
    serializer_class = BuildingSerializer
    @action(detail=True, methods=['get'])
    def areas(self, request, pk=None):
        building = self.get_object()
        areas = Area.objects.filter(type=building)
        serializer = AreaSerializer(areas, many=True)
        return Response(serializer.data)    


class AreaViewSet(viewsets.ModelViewSet):
    queryset = Area.objects.all()
    serializer_class = AreaSerializer

    @action(detail=True, methods=['get'])
    def data(self, request, pk=None):
        area = self.get_object()
        data = area.bound_node
        serializer = HardwareNodeSerializer(data)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def popular(self, request):
        count = int(request.query_params.get('count', 5))
        areas = Area.objects.all()
        areas = sorted(areas, key=lambda x: x.bound_node.detected_count, reverse=True)[:count]
        serializer = AreaSerializer(areas, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def historical(self, request, pk=None):
        area = self.get_object()
        historical_data = HistoricalData.objects.filter(area=area)
        serializer = HistoricalDataSerializer(historical_data, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def favor(self, request, pk=None):
        if not request.user.is_authenticated:
            return Response({"detail": "请先登录"}, status=status.HTTP_401_UNAUTHORIZED)
        area = self.get_object()
        if request.user.favorite_areas.filter(id=area.id).exists():
            request.user.favorite_areas.remove(area)
            request.user.save()
            return Response({"detail": "区域已取消收藏"})
        else:
            request.user.favorite_areas.add(area)
            request.user.save()
            return Response({"detail": "区域已收藏"})





class HistoricalDataViewSet(viewsets.ModelViewSet):
    queryset = HistoricalData.objects.all()
    serializer_class = HistoricalDataSerializer

    @action(detail=False, methods=['get'])
    def latest(self, request):
        count = int(request.query_params.get('count', 5))
        historical_data = self.queryset.order_by('-timestamp')[:count]
        serializer = HistoricalDataSerializer(historical_data, many=True)
        return Response(serializer.data)


class AlertViewSet(viewsets.ModelViewSet):
    queryset = Alert.objects.all()
    serializer_class = AlertSerializer

    @action(detail=False, methods=['get'])
    def list(self, request):
        alerts = self.queryset.filter(solved=False).order_by('-timestamp')
        serializer = AlertSerializer(alerts, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def solve(self, request, pk=None):
        alert = self.get_object()
        alert.solved = True
        alert.save()
        return Response({"detail": "Alert marked as solved."})


class NoticeViewSet(viewsets.ModelViewSet):
    queryset = Notice.objects.all()
    serializer_class = NoticeSerializer

    @action(detail=False, methods=['get'])
    def latest(self, request):
        count = int(request.query_params.get('count', 5))
        notices = self.queryset.order_by('-timestamp')[:count]
        serializer = NoticeSerializer(notices, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def areas(self, request, pk=None):
        notice = self.get_object()
        areas = notice.related_areas.all()
        serializer = AreaSerializer(areas, many=True)
        return Response(serializer.data)


class AlertView(APIView):
    def post(self, request):
        # 使用 AlertSerializer 解析上传的数据
        serializer = AlertSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # 获取上传的数据
        try:
            area = serializer.validated_data['area']
            alert_type = serializer.validated_data['alert_type']
            grade = serializer.validated_data['grade']
            publicity = serializer.validated_data['publicity']
            message = serializer.validated_data['message']
        except KeyError as e:
            return Response({"error": f"缺失字段: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

        # 创建告警记录
        alert = Alert(
            area=area,
            alert_type=alert_type,
            grade=grade,
            publicity=publicity,
            message=message
        )
        alert.save()
        return Response({"message": "告警创建成功"}, status=status.HTTP_201_CREATED)


class DataUploadView(APIView):
    def post(self, request):
        # 使用 HardwareNodeUploadSerializer 解析上传的数据
        serializer = DataUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # 获取上传的数据
        try:
            hardware_node_id = serializer.validated_data['id']
            detected_count = serializer.validated_data['detected_count']
            timestamp = serializer.validated_data['timestamp']
        except KeyError as e:
            return Response({"error": f"缺失字段: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # 获取硬件节点
            hardware_node = HardwareNode.objects.get(id=hardware_node_id)
            hardware_node.detected_count = detected_count
            hardware_node.updated_at = timestamp
            hardware_node.save()
        except HardwareNode.DoesNotExist:
            return Response({"error": "硬件节点不存在"}, status=status.HTTP_404_NOT_FOUND)

        # 获取硬件节点绑定的区域
        try:
            area = Area.objects.get(bound_node=hardware_node)
        except Area.DoesNotExist:
            return Response({"error": "硬件节点未绑定到任何区域"}, status=status.HTTP_404_NOT_FOUND)

        # 保存到 HistoricalData 模型
        historical_data = HistoricalData(
            area=area,
            detected_count=detected_count,
            timestamp=timestamp
        )
        historical_data.save()
        return Response({"message": "检测结果上传成功"}, status=status.HTTP_201_CREATED)


class SummaryView(APIView):
    def get(self, request):
        nodes_count = HardwareNode.objects.count()
        terminals_count = ProcessTerminal.objects.count()
        buildings_count = Building.objects.count()
        areas_count = Area.objects.count()
        historical_data_count = HistoricalData.objects.count()
        people_count = get_summary_people_count()
        return Response({
            "nodes_count": nodes_count,
            "terminals_count": terminals_count,
            "buildings_count": buildings_count,
            "areas_count": areas_count,
            "historical_data_count": historical_data_count,
            "people_count": people_count
        })