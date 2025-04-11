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
        fields = ['id', 'name', 'detected_count', 'terminal', 'status', 'updated_at', 'description']


class ProcessTerminalSerializer(serializers.ModelSerializer):
    nodes_count = serializers.SerializerMethodField()

    class Meta:
        model = ProcessTerminal
        fields = ['id', 'name', 'status', 'nodes_count']

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
    detected_count = serializers.IntegerField(source='bound_node.detected_count', read_only=True)
    is_favorite = serializers.SerializerMethodField()
    class Meta:
        model = Area
        fields = ['id', 'name', 'bound_node', 'description', 'type', 'floor', 'capacity', 'detected_count', 'is_favorite']
    def get_is_favorite(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return request.user.favorite_areas.filter(id=obj.id).exists()
        return False

class HistoricalDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = HistoricalData
        fields = ['id', 'area', 'detected_count', 'timestamp']


class DataUploadSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    detected_count = serializers.IntegerField()
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