from rest_framework import viewsets
from rest_framework.decorators import action
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

class HistoricalDataViewSet(viewsets.ModelViewSet):
    queryset = HistoricalData.objects.all()
    serializer_class = HistoricalDataSerializer

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
    def get(self):
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