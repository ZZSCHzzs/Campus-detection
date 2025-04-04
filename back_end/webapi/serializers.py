from .models import *
from rest_framework import serializers

class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'role', 'phone', 'email', 'register_time']

class HardwareNodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = HardwareNode
        fields = ['id', 'name', 'detected_count', 'terminal', 'status', 'updated_at', 'description']

class ProcessTerminalSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcessTerminal
        fields = ['id', 'name', 'status']

class BuildingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Building
        fields = ['id', 'name', 'description']

class AreaSerializer(serializers.ModelSerializer):
    detected_count = serializers.IntegerField(source='bound_node.detected_count', read_only=True)
    class Meta:
        model = Area
        fields = ['id', 'name', 'bound_node', 'description', 'type', 'floor', 'capacity', 'detected_count']

class HistoricalDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = HistoricalData
        fields = ['id', 'area', 'detected_count', 'timestamp']

class DataUploadSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    detected_count = serializers.IntegerField()
    timestamp = serializers.DateTimeField()
