from .models import *
from rest_framework import serializers
from djoser.serializers import UserCreateSerializer

class CustomUserCreateSerializer(UserCreateSerializer):
    class Meta(UserCreateSerializer.Meta):
        model = CustomUser
        fields = ('id', 'username', 'email', 'password', 'role', 'phone')

    def create(self, validated_data):
        # 确保新用户被激活
        validated_data['is_active'] = True
        user = super().create(validated_data)
        return user

class CustomUserSerializer(serializers.ModelSerializer):
    favorite_areas = serializers.PrimaryKeyRelatedField(
        many=True,
        read_only=True,
    )
    role = serializers.ChoiceField(choices=CustomUser.ROLE_CHOICES, default='user')
    phone = serializers.CharField(max_length=20, required=False)
    register_time = serializers.DateTimeField(read_only=True)
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'role', 'phone', 'email', 'register_time', 'favorite_areas',]

class HardwareNodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = HardwareNode
        fields = ['id', 'name', 'detected_count', 'terminal', 'status', 'updated_at', 'description', 'temperature', 'humidity']


class ProcessTerminalSerializer(serializers.ModelSerializer):
    nodes_count = serializers.SerializerMethodField()

    class Meta:
        model = ProcessTerminal
        fields = ['id', 'name', 'status', 'nodes_count', 'co2_level', 'co2_status']

    def get_nodes_count(self, obj):
        return HardwareNode.objects.filter(terminal=obj).count()


class BuildingSerializer(serializers.ModelSerializer):
    areas_count = serializers.SerializerMethodField()

    class Meta:
        model = Building
        fields = ['id', 'name', 'description', 'areas_count']

    def get_areas_count(self, obj):
        return Area.objects.filter(type=obj).count()


class AreaSerializer(serializers.ModelSerializer):
    detected_count = serializers.SerializerMethodField()
    is_favorite = serializers.SerializerMethodField()
    node_status = serializers.SerializerMethodField()
    
    class Meta:
        model = Area
        fields = ['id', 'name', 'bound_node', 'description', 'type', 'floor', 'capacity', 'detected_count', 'is_favorite', 'node_status']
    
    def get_detected_count(self, obj):
        # 针对none节点(id=12)的优化处理
        if obj.bound_node_id == 12:
            # 对于none节点，返回默认值或缓存值
            return 0
        return obj.bound_node.detected_count if obj.bound_node else 0
    
    def get_node_status(self, obj):
        # 针对none节点的状态优化
        if obj.bound_node_id == 12:
            return 'none'  # 标记为none节点
        return 'normal'
    
    def get_is_favorite(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return request.user.favorite_areas.filter(id=obj.id).exists()
        return False

# 新增：轻量级区域序列化器（用于列表显示）
class AreaLightSerializer(serializers.ModelSerializer):
    detected_count = serializers.SerializerMethodField()
    node_status = serializers.SerializerMethodField()
    
    class Meta:
        model = Area
        fields = ['id', 'name', 'floor', 'capacity', 'detected_count', 'node_status']
    
    def get_detected_count(self, obj):
        if obj.bound_node_id == 12:
            return 0
        return obj.bound_node.detected_count if obj.bound_node else 0
    
    def get_node_status(self, obj):
        if obj.bound_node_id == 12:
            return 'none'
        return 'normal'

class HistoricalDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = HistoricalData
        fields = ['id', 'area', 'detected_count', 'timestamp']


class TemperatureHumidityDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = TemperatureHumidityData
        fields = ['id', 'area', 'temperature', 'humidity', 'timestamp']


class CO2DataSerializer(serializers.ModelSerializer):
    class Meta:
        model = CO2Data
        fields = ['id', 'terminal', 'co2_level', 'timestamp']


class DataUploadSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    detected_count = serializers.IntegerField()
    timestamp = serializers.DateTimeField()
    temperature = serializers.FloatField(required=False, allow_null=True)
    humidity = serializers.FloatField(required=False, allow_null=True)


class TemperatureHumidityUploadSerializer(serializers.Serializer):
    area_id = serializers.IntegerField()
    temperature = serializers.FloatField(required=False, allow_null=True)
    humidity = serializers.FloatField(required=False, allow_null=True)
    timestamp = serializers.DateTimeField()


class CO2UploadSerializer(serializers.Serializer):
    terminal_id = serializers.IntegerField()
    co2_level = serializers.IntegerField()
    timestamp = serializers.DateTimeField()

class AlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = Alert
        fields = ['id', 'area', 'alert_type', 'timestamp', 'grade', 'publicity', 'solved', 'message']

    def validate_grade(self, value):
        if value not in [0, 1, 2, 3]:
            raise serializers.ValidationError("告警等级必须在0-3之间")
        return value

    def validate_alert_type(self, value):
        valid_types = ['fire', 'guard', 'crowd', 'health', 'other']
        if value not in valid_types:
            raise serializers.ValidationError(f"告警类型必须是以下之一: {', '.join(valid_types)}")
        return value

class NoticeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notice
        fields = ['id', 'title', 'content', 'timestamp', 'related_areas']