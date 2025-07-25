from rest_framework import viewsets
from rest_framework.decorators import action, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.core.cache import cache
import json
import logging
from django.utils import timezone
from .models import *
from .serializers import *
from .permissions import StaffEditSelected



logger = logging.getLogger('django')

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
    
    @action(detail=True, methods=['get'])
    def co2_data(self, request, pk=None):
        terminal = self.get_object()
        hours = int(request.query_params.get('hours', 24))
        from_time = timezone.now() - timezone.timedelta(hours=hours)
        
        data = CO2Data.objects.filter(
            terminal=terminal,
            timestamp__gte=from_time
        ).order_by('timestamp')
        serializer = CO2DataSerializer(data, many=True)
        return Response(serializer.data)
        
    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """获取终端状态"""
        terminal = self.get_object()
        
        cache_key = f"terminal:{pk}:status"
        cached_status = cache.get(cache_key)
        
        if cached_status:
            logger.debug(f"从缓存获取终端{pk}状态")
            # 确保摄像头数据存在且格式正确
            if 'nodes' not in cached_status or cached_status['nodes'] is None:
                cached_status['nodes'] = {}
            # 补全所有可能的字段
            cached_status.setdefault('cpu_usage', getattr(terminal, 'cpu_usage', 0))
            cached_status.setdefault('memory_usage', getattr(terminal, 'memory_usage', 0))
            cached_status.setdefault('disk_usage', getattr(terminal, 'disk_usage', 0))
            cached_status.setdefault('disk_free', getattr(terminal, 'disk_free', 0))
            cached_status.setdefault('disk_total', getattr(terminal, 'disk_total', 0))
            cached_status.setdefault('memory_available', getattr(terminal, 'memory_available', 0))
            cached_status.setdefault('memory_total', getattr(terminal, 'memory_total', 0))
            cached_status.setdefault('co2_level', getattr(terminal, 'co2_level', -1))
            cached_status.setdefault('co2_status', getattr(terminal, 'co2_status', '未连接'))
            cached_status.setdefault('system_uptime', getattr(terminal, 'system_uptime', None))
            cached_status.setdefault('frame_rate', getattr(terminal, 'frame_rate', None))
            cached_status.setdefault('total_frames', getattr(terminal, 'total_frames', None))
            cached_status.setdefault('terminal_online', getattr(terminal, 'status', False))
            cached_status.setdefault('terminal_id', getattr(terminal, 'terminal_id', terminal.id))
            cached_status.setdefault('mode', getattr(terminal, 'mode', 'both'))
            cached_status.setdefault('last_detection', getattr(terminal, 'last_detection', {}))
            cached_status.setdefault('model_loaded', getattr(terminal, 'model_loaded', False))
            cached_status.setdefault('push_running', getattr(terminal, 'push_running', False))
            cached_status.setdefault('pull_running', getattr(terminal, 'pull_running', False))
            return Response(cached_status)
        
        if not terminal.status:
            default_status = {
                "model_loaded": False,
                "push_running": False,
                "pull_running": False,
                "cpu_usage": 0,
                "memory_usage": 0,
                "disk_usage": 0,
                "disk_free": 0,
                "disk_total": 0,
                "memory_available": 0,
                "memory_total": 0,
                "co2_level": getattr(terminal, 'co2_level', -1),
                "co2_status": getattr(terminal, 'co2_status', '未连接'),
                "system_uptime": getattr(terminal, 'system_uptime', None),
                "frame_rate": getattr(terminal, 'frame_rate', None),
                "total_frames": getattr(terminal, 'total_frames', None),
                "nodes": {},
                "terminal_online": False,
                "terminal_id": getattr(terminal, 'terminal_id', terminal.id),
                "mode": getattr(terminal, 'mode', 'both'),
                "last_detection": getattr(terminal, 'last_detection', {})
            }
            cache.set(cache_key, default_status, timeout=30)
            return Response(default_status)
        
        try:
            nodes_data = terminal.nodes or {}
            status_data = {
                "model_loaded": terminal.model_loaded if hasattr(terminal, 'model_loaded') else False,
                "push_running": terminal.push_running,
                "pull_running": terminal.pull_running,
                "cpu_usage": terminal.cpu_usage or 0,
                "memory_usage": terminal.memory_usage or 0,
                "disk_usage": getattr(terminal, 'disk_usage', 0),
                "disk_free": getattr(terminal, 'disk_free', 0),
                "disk_total": getattr(terminal, 'disk_total', 0),
                "memory_available": getattr(terminal, 'memory_available', 0),
                "memory_total": getattr(terminal, 'memory_total', 0),
                "co2_level": getattr(terminal, 'co2_level', -1),
                "co2_status": getattr(terminal, 'co2_status', '未连接'),
                "system_uptime": getattr(terminal, 'system_uptime', None),
                "frame_rate": getattr(terminal, 'frame_rate', None),
                "total_frames": getattr(terminal, 'total_frames', None),
                "nodes": nodes_data,
                "terminal_online": terminal.status,
                "terminal_id": getattr(terminal, 'terminal_id', terminal.id),
                "mode": getattr(terminal, 'mode', 'both'),
                "last_detection": getattr(terminal, 'last_detection', {})
            }
            cache.set(cache_key, status_data, timeout=60)
            logger.debug(f"更新终端{pk}状态缓存，节点: {nodes_data}")
            return Response(status_data)
        except Exception as e:
            logger.error(f"获取终端{pk}状态失败: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'])
    def logs(self, request, pk=None):
        """获取终端日志（仅从Redis缓存，不从数据库字段）"""
        terminal = self.get_object()
        limit = int(request.query_params.get('limit', 100))
        cache_key = f"terminal:{pk}:logs"
        cached_logs = cache.get(cache_key)
        if cached_logs:
            logger.debug(f"从缓存获取终端{pk}日志")
            if limit and limit < len(cached_logs):
                return Response(cached_logs[:limit])
            return Response(cached_logs)
        # 没有缓存则返回空列表并写入缓存
        empty_logs = []
        cache.set(cache_key, empty_logs, timeout=120)
        logger.debug(f"设置空日志缓存: {cache_key}")
        return Response(empty_logs)

    @action(detail=True, methods=['get', 'post'])
    def config(self, request, pk=None):
        """获取或更新终端配置（节点配置只从Redis缓存，不从数据库字段nodes）"""
        terminal = self.get_object()
        cache_key = f"terminal:{pk}:config"
        if request.method == 'GET':
            cached_config = cache.get(cache_key)
            if cached_config:
                logger.debug(f"从缓存获取终端{pk}配置")
                return Response(cached_config)
            # 构建配置数据（节点配置只从Redis缓存）
            config_data = {
                "mode": terminal.mode or "both",
                "interval": terminal.interval or 5,
                "nodes": terminal.node_config or {},  # node_config为实际配置
                "save_image": getattr(terminal, 'save_image', True),
                "preload_model": getattr(terminal, 'preload_model', True),
                "co2_enabled": getattr(terminal, 'co2_enabled', True),
                "co2_read_interval": getattr(terminal, 'co2_read_interval', 30)
            }
            cache.set(cache_key, config_data, timeout=300)
            return Response(config_data)
        else:
            # 更新配置并同步到缓存
            try:
                channel_layer = get_channel_layer()
                message = {
                    'type': 'send_command',
                    'command': 'update_config',
                    'params': request.data,
                    'timestamp': timezone.now().isoformat()
                }
                async_to_sync(channel_layer.group_send)(
                    f"terminal_{pk}",
                    message
                )
                # 保存到数据库
                if 'mode' in request.data:
                    terminal.mode = request.data['mode']
                if 'interval' in request.data:
                    terminal.interval = request.data['interval']
                if 'nodes' in request.data:
                    terminal.node_config = request.data['nodes']
                if 'save_image' in request.data:
                    terminal.save_image = request.data['save_image']
                if 'preload_model' in request.data:
                    terminal.preload_model = request.data['preload_model']
                if 'co2_enabled' in request.data:
                    terminal.co2_enabled = request.data['co2_enabled']
                if 'co2_read_interval' in request.data:
                    terminal.co2_read_interval = request.data['co2_read_interval']
                terminal.save()
                # 更新Redis缓存
                config_data = {
                    "mode": terminal.mode,
                    "interval": terminal.interval,
                    "nodes": terminal.node_config,
                    "save_image": getattr(terminal, 'save_image', True),
                    "preload_model": getattr(terminal, 'preload_model', True),
                    "co2_enabled": getattr(terminal, 'co2_enabled', True),
                    "co2_read_interval": getattr(terminal, 'co2_read_interval', 30)
                }
                cache.set(cache_key, config_data, timeout=300)
                return Response({"status": "success", "message": "配置已更新"})
            except Exception as e:
                logger.error(f"更新终端{pk}配置失败: {str(e)}")
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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

    @action(detail=True, methods=['get'],permission_classes=[IsAuthenticated])
    def temperature_humidity(self, request, pk=None):
        area = self.get_object()
        hours = int(request.query_params.get('hours', 24))
        from_time = timezone.now() - timezone.timedelta(hours=hours)
        
        data = TemperatureHumidityData.objects.filter(
            area=area,
            timestamp__gte=from_time
        ).order_by('timestamp')
        serializer = TemperatureHumidityDataSerializer(data, many=True)
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


class TemperatureHumidityDataViewSet(viewsets.ModelViewSet):
    queryset = TemperatureHumidityData.objects.all()
    serializer_class = TemperatureHumidityDataSerializer
    permission_classes = [StaffEditSelected]
    allow_staff_edit = False

    @action(detail=False, methods=['get'])
    def latest(self, request):
        count = int(request.query_params.get('count', 10))
        data = self.queryset.order_by('-timestamp')[:count]
        serializer = TemperatureHumidityDataSerializer(data, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_area(self, request):
        area_id = request.query_params.get('area_id')
        if not area_id:
            return Response({"error": "需要提供area_id参数"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            area = Area.objects.get(id=area_id)
        except Area.DoesNotExist:
            return Response({"error": "区域不存在"}, status=status.HTTP_404_NOT_FOUND)
        
        hours = int(request.query_params.get('hours', 24))
        from_time = timezone.now() - timezone.timedelta(hours=hours)
        
        data = self.queryset.filter(
            area=area,
            timestamp__gte=from_time
        ).order_by('timestamp')
        
        serializer = TemperatureHumidityDataSerializer(data, many=True)
        return Response(serializer.data)


class CO2DataViewSet(viewsets.ModelViewSet):
    queryset = CO2Data.objects.all()
    serializer_class = CO2DataSerializer
    permission_classes = [StaffEditSelected]
    allow_staff_edit = False

    @action(detail=False, methods=['get'])
    def latest(self, request):
        count = int(request.query_params.get('count', 10))
        data = self.queryset.order_by('-timestamp')[:count]
        serializer = CO2DataSerializer(data, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_terminal(self, request):
        terminal_id = request.query_params.get('terminal_id')
        if not terminal_id:
            return Response({"error": "需要提供terminal_id参数"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            terminal = ProcessTerminal.objects.get(id=terminal_id)
        except ProcessTerminal.DoesNotExist:
            return Response({"error": "终端不存在"}, status=status.HTTP_404_NOT_FOUND)
        
        hours = int(request.query_params.get('hours', 24))
        from_time = timezone.now() - timezone.timedelta(hours=hours)
        
        data = self.queryset.filter(
            terminal=terminal,
            timestamp__gte=from_time
        ).order_by('timestamp')
        
        serializer = CO2DataSerializer(data, many=True)
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
            temperature = serializer.validated_data.get['temperature']
            humidity = serializer.validated_data.get['humidity']
        except KeyError as e:
            return Response({"error": f"缺失字段: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # 获取硬件节点
            hardware_node = HardwareNode.objects.get(id=hardware_node_id)
            hardware_node.detected_count = detected_count
            hardware_node.updated_at = timestamp
            
            # 保存环境数据
            if temperature is not None:
                hardware_node.temperature = temperature
            if humidity is not None:
                hardware_node.humidity = humidity
                
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


class TemperatureHumidityUploadView(APIView):
    def post(self, request):
        serializer = TemperatureHumidityUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            area_id = serializer.validated_data['area_id']
            temperature = serializer.validated_data.get('temperature')
            humidity = serializer.validated_data.get('humidity')
            timestamp = serializer.validated_data['timestamp']
        except KeyError as e:
            return Response({"error": f"缺失字段: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            area = Area.objects.get(id=area_id)
        except Area.DoesNotExist:
            return Response({"error": "区域不存在"}, status=status.HTTP_404_NOT_FOUND)

        # 保存温湿度数据记录
        temp_humidity_data = TemperatureHumidityData(
            area=area,
            temperature=temperature,
            humidity=humidity,
            timestamp=timestamp
        )
        temp_humidity_data.save()
        return Response({"message": "温湿度数据上传成功"}, status=status.HTTP_201_CREATED)


class CO2UploadView(APIView):
    def post(self, request):
        serializer = CO2UploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            terminal_id = serializer.validated_data['terminal_id']
            co2_level = serializer.validated_data['co2_level']
            timestamp = serializer.validated_data['timestamp']
        except KeyError as e:
            return Response({"error": f"缺失字段: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            terminal = ProcessTerminal.objects.get(id=terminal_id)
        except ProcessTerminal.DoesNotExist:
            return Response({"error": "终端不存在"}, status=status.HTTP_404_NOT_FOUND)

        # 保存CO2数据记录
        co2_data = CO2Data(
            terminal=terminal,
            co2_level=co2_level,
            timestamp=timestamp
        )
        co2_data.save()
        return Response({"message": "CO2数据上传成功"}, status=status.HTTP_201_CREATED)


class SummaryView(APIView):

    def get(self, request):
        nodes_count = HardwareNode.objects.count()
        nodes_online_count = HardwareNode.objects.filter(status=True).count()        
        terminals_count = ProcessTerminal.objects.count()
        terminals_online_count = ProcessTerminal.objects.filter(status=True).count()
        buildings_count = Building.objects.count()
        areas_count = Area.objects.count()
        historical_data_count = HistoricalData.objects.count()
        people_count = get_summary_people_count()
        notice_count = Notice.objects.count()
        alerts_count = Alert.objects.count()
        users_count = CustomUser.objects.count()
        return Response({
            "nodes_count": nodes_count,
            "terminals_count": terminals_count,
            "buildings_count": buildings_count,
            "areas_count": areas_count,
            "historical_data_count": historical_data_count,
            "people_count": people_count,
            "notice_count": notice_count,
            "alerts_count": alerts_count,
            "users_count": users_count,
            "nodes_online_count": nodes_online_count,
            "terminals_online_count": terminals_online_count
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
            
            # 更新终端的最后活动时间
            terminal.last_active = timezone.now()
            terminal.save(update_fields=['last_active'])
            
            # 处理特殊命令 - 实时更新缓存
            command = command_data.get('command')
            params = command_data.get('params', {})
            
            if command == "start":
                mode = params.get('mode')
                if mode == 'pull' or mode == 'both':
                    terminal.pull_running = True
                if mode == 'push' or mode == 'both':
                    terminal.push_running = True
                terminal.save(update_fields=['pull_running', 'push_running'])
                
                # 更新状态缓存
                self._update_status_cache(pk, terminal)
                
            elif command == "stop":
                mode = params.get('mode')
                if mode == 'pull' or mode == 'both':
                    terminal.pull_running = False
                if mode == 'push' or mode == 'both':
                    terminal.push_running = False
                terminal.save(update_fields=['pull_running', 'push_running'])
                
                # 更新状态缓存
                self._update_status_cache(pk, terminal)
            
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
            logger.error(f"发送命令到终端{pk}失败: {str(e)}")
            return Response(
                {"error": f"发送命令失败: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
    def _update_status_cache(self, terminal_id, terminal):
        """更新终端状态缓存"""
        cache_key = f"terminal:{terminal_id}:status"
        status_data = {
            "model_loaded": terminal.model_loaded,
            "push_running": terminal.push_running,
            "pull_running": terminal.pull_running,
            "cpu_usage": terminal.cpu_usage or 0,
            "memory_usage": terminal.memory_usage or 0,
            "co2_level": terminal.co2_level,  # 添加CO2字段
            "nodes": terminal.nodes or {}
        }
        cache.set(cache_key, status_data, timeout=60)  # 1分钟过期


# 添加环境信息API
class EnvironmentView(APIView):
    """返回环境信息，帮助前端识别当前运行环境"""
    
    def get(self, request):
        return Response({
            "type": "server",
            "version": "2.0.0",
            "name": "服务端",
            "id": 0,
            "features": {
                "local_detection": False,
                "websocket": True,
                "push_mode": False,
                "pull_mode": False
            }
        })