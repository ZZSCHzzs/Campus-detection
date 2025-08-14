from rest_framework import serializers
from .models import (
    LLMAnalysis, UserRecommendation, AlertAnalysis, AreaUsagePattern, GeneratedContent
)
import json

class LLMAnalysisSerializer(serializers.ModelSerializer):
    area_name = serializers.ReadOnlyField(source='area.name')
    area_location = serializers.ReadOnlyField(source='area.type.name')
    parsed_data = serializers.SerializerMethodField()
    
    class Meta:
        model = LLMAnalysis
        fields = ['id', 'area', 'area_name', 'area_location', 'timestamp', 
                 'analysis_text', 'analysis_data', 'parsed_data', 
                 'alert_status', 'alert_message']
    
    def get_parsed_data(self, obj):
        """将JSON字符串解析为Python对象"""
        if obj.analysis_data:
            try:
                return json.loads(obj.analysis_data)
            except json.JSONDecodeError:
                return None
        return None

class UserRecommendationSerializer(serializers.ModelSerializer):
    area_name = serializers.ReadOnlyField(source='area.name')
    area_building = serializers.ReadOnlyField(source='area.type.name')
    username = serializers.ReadOnlyField(source='user.username')
    
    class Meta:
        model = UserRecommendation
        fields = ['id', 'user', 'username', 'area', 'area_name', 'area_building', 
                 'score', 'reason', 'timestamp', 'clicked']

class AlertAnalysisSerializer(serializers.ModelSerializer):
    alert_type = serializers.ReadOnlyField(source='alert.alert_type')
    area_name = serializers.ReadOnlyField(source='alert.area.name')
    alert_grade = serializers.ReadOnlyField(source='alert.grade')
    alert_message = serializers.ReadOnlyField(source='alert.message')
    
    class Meta:
        model = AlertAnalysis
        fields = ['id', 'alert', 'alert_type', 'area_name', 'alert_grade', 'alert_message',
                 'analysis_text', 'priority_score', 'handling_suggestions', 
                 'potential_causes', 'timestamp']

class AreaUsagePatternSerializer(serializers.ModelSerializer):
    area_name = serializers.ReadOnlyField(source='area.name')
    building_name = serializers.ReadOnlyField(source='area.type.name')
    
    class Meta:
        model = AreaUsagePattern
        fields = ['id', 'area', 'area_name', 'building_name', 'daily_pattern', 
                 'weekly_pattern', 'peak_hours', 'quiet_hours', 
                 'average_duration', 'typical_user_groups', 'last_updated']

class GeneratedContentSerializer(serializers.ModelSerializer):
    content_type_display = serializers.ReadOnlyField(source='get_content_type_display')
    area_name = serializers.SerializerMethodField()
    
    class Meta:
        model = GeneratedContent
        fields = ['id', 'content_type', 'content_type_display', 'title', 'content',
                 'related_area', 'area_name', 'generated_at', 'published']
    
    def get_area_name(self, obj):
        if obj.related_area:
            return obj.related_area.name
        return None