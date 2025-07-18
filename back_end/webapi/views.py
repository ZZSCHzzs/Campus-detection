from rest_framework import viewsets
from rest_framework.decorators import action, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import json
from .models import *
from .serializers import *
from .permissions import StaffEditSelected



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
    permission_classes = [StaffEditSelected]
    allow_staff_edit = False

    def get_permissions(self):
        if self.action == 'create':
            return []  # 开放注册
        elif self.action in ['update', 'partial_update', 'destroy']:
            return [IsAdminUser()]  # 写操作仅限管理员
        return super().get_permissions()

    def destroy(self, request, *args, **kwargs):
        """安全删除（标记禁用而非真删除）"""
        instance = self.get_object()
        if instance.is_superuser:
            return Response(
                {"detail": "不能删除超级管理员"},
                status=status.HTTP_403_FORBIDDEN
            )

        instance.is_active = False
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'])
    def me(self, request):
        """获取当前用户信息"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)


class HardwareNodeViewSet(viewsets.ModelViewSet):
    queryset = HardwareNode.objects.all()
    serializer_class = HardwareNodeSerializer
    permission_classes = [StaffEditSelected]
    allow_staff_edit = False


class ProcessTerminalViewSet(viewsets.ModelViewSet):
    queryset = ProcessTerminal.objects.all()
    serializer_class = ProcessTerminalSerializer
    permission_classes = [StaffEditSelected]
    allow_staff_edit = False

    @action(detail=True, methods=['get'])
    def nodes(self, request, pk=None):
        terminal = self.get_object()
        nodes = HardwareNode.objects.filter(terminal=terminal)
        serializer = HardwareNodeSerializer(nodes, many=True)
        return Response(serializer.data)


class BuildingViewSet(viewsets.ModelViewSet):
    queryset = Building.objects.all()
    serializer_class = BuildingSerializer
    permission_classes = [StaffEditSelected]
    allow_staff_edit = False
    @action(detail=True, methods=['get'])
    def areas(self, request, pk=None):
        building = self.get_object()
        areas = Area.objects.filter(type=building)
        serializer = AreaSerializer(areas, many=True, context={'request': request})
        return Response(serializer.data)    


class AreaViewSet(viewsets.ModelViewSet):
    queryset = Area.objects.all()
    serializer_class = AreaSerializer
    permission_classes = [StaffEditSelected]
    allow_staff_edit = False

    @action(detail=True, methods=['get'])
    def data(self, request,  pk=None):
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

    @action(detail=True, methods=['get'],permission_classes=[IsAuthenticated])
    def historical(self, request, pk=None):
        area = self.get_object()
        historical_data = HistoricalData.objects.filter(area=area)
        serializer = HistoricalDataSerializer(historical_data, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def favor(self, request, pk=None):

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
    permission_classes = [StaffEditSelected]
    allow_staff_edit = False  # 标记该资源允许 Staff 编辑

    @action(detail=False, methods=['get'])
    def latest(self, request):
        count = int(request.query_params.get('count', 5))
        historical_data = self.queryset.order_by('-timestamp')[:count]
        serializer = HistoricalDataSerializer(historical_data, many=True)
        return Response(serializer.data)


class AlertViewSet(viewsets.ModelViewSet):
    queryset = Alert.objects.all()
    serializer_class = AlertSerializer
    permission_classes = [StaffEditSelected]
    allow_staff_edit = True  # 标记该资源允许 Staff 编辑

    @action(detail=False, methods=['get'])
    def unsolved(self, request):
        alerts = self.queryset.filter(solved=False).order_by('-timestamp')
        serializer = AlertSerializer(alerts, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def solve(self, request, pk=None):
        alert = self.get_object()
        if(alert.solved):
            return Response({"detail": "Alert already solved."}, status=status.HTTP_400_BAD_REQUEST)
        alert.solved = True
        alert.save()
        return Response({"detail": "Alert marked as solved."})

    @action(detail=False, methods=['get'])
    def public(self, request):
        alerts = self.queryset.filter(publicity=True, solved=False).order_by('-timestamp')
        serializer = AlertSerializer(alerts, many=True)
        return Response(serializer.data)


class NoticeViewSet(viewsets.ModelViewSet):
    queryset = Notice.objects.all()
    serializer_class = NoticeSerializer
    permission_classes = [StaffEditSelected]
    allow_staff_edit = True

    @action(detail=False, methods=['get'])
    def latest(self, request):
        count = int(request.query_params.get('count', 5))
        notices = self.queryset.filter(outdated=False).order_by('-timestamp')[:count]
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
            node = serializer.validated_data['id']
            alert_type = serializer.validated_data['alert_type']
            grade = serializer.validated_data['grade']
            publicity = serializer.validated_data['publicity']
            message = serializer.validated_data['message']
        except KeyError as e:
            return Response({"error": f"缺失字段: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

        # 创建告警记录
        alert = Alert(
            area=Area.objects.get(bound_node=node),
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
        notice_count = Notice.objects.count()
        alerts_count = Alert.objects.count()
        return Response({
            "nodes_count": nodes_count,
            "terminals_count": terminals_count,
            "buildings_count": buildings_count,
            "areas_count": areas_count,
            "historical_data_count": historical_data_count,
            "people_count": people_count,
            "notice_count": notice_count,
            "alerts_count": alerts_count
        })


class TerminalCommandView(APIView):
    """
    用于发送命令到检测终端
    """
    permission_classes = [StaffEditSelected]
    allow_staff_edit = True
    
    def post(self, request, pk=None):
        """
        向指定ID的终端发送命令
        """
        try:
            # 验证终端是否存在
            terminal = ProcessTerminal.objects.get(id=pk)
            
            # 获取命令数据
            command_data = request.data
            if not isinstance(command_data, dict) or 'command' not in command_data:
                return Response(
                    {"error": "必须提供有效的命令格式，包含'command'字段"},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            # 构建命令消息
            message = {
                'type': 'send_command',
                'command': command_data.get('command'),
                'params': command_data.get('params', {}),
                'timestamp': timezone.now().isoformat()
            }
            
            # 获取通道层
            channel_layer = get_channel_layer()
            
            # 发送命令到终端的消费者
            channel_name = f"terminal_{pk}"
            async_to_sync(channel_layer.group_send)(
                channel_name,
                message
            )
            
            return Response({
                "status": "success",
                "message": f"命令已发送到终端 {pk}",
                "command": command_data
            })
            
        except ProcessTerminal.DoesNotExist:
            return Response(
                {"error": f"终端ID {pk} 不存在"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": f"发送命令失败: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# 添加环境信息API
class EnvironmentView(APIView):
    """返回环境信息，帮助前端识别当前运行环境"""
    
    def get(self, request):
        return Response({
            "type": "server",  # 标识这是服务端
            "version": "2.0.0",
            "name": "检测服务中心",
            "id": 0,  # 服务端ID为0
            "features": {
                "local_detection": False,
                "websocket": True,
                "push_mode": False,
                "pull_mode": False
            }
        })