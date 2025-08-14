from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.views import APIView
from django.http import StreamingHttpResponse
from django.utils import timezone
from datetime import timedelta
import requests
import os
import json

from .models import LLMAnalysis, UserRecommendation, AlertAnalysis, AreaUsagePattern, GeneratedContent
from .serializers import (
    LLMAnalysisSerializer, UserRecommendationSerializer,
    AlertAnalysisSerializer, AreaUsagePatternSerializer, GeneratedContentSerializer
)
from webapi.models import Area, Alert, CustomUser
from .tasks import (
    analyze_area_data, analyze_alert,
    generate_area_usage_pattern, generate_personalized_recommendations
)
from .agent import get_agent_response


class LLMAnalysisViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LLMAnalysis.objects.all().order_by('-timestamp')
    serializer_class = LLMAnalysisSerializer

    @action(detail=True, methods=['post'], url_path='analyze')
    def analyze_area(self, request, pk=None):
        try:
            area = Area.objects.get(pk=pk)
        except Area.DoesNotExist:
            return Response({"error": "Area not found"}, status=status.HTTP_404_NOT_FOUND)

        # Check for recent analysis (e.g., within the last hour)
        recent_analysis = self.get_queryset().filter(
            area=area,
            timestamp__gte=timezone.now() - timedelta(hours=1)
        ).first()

        if recent_analysis:
            serializer = self.get_serializer(recent_analysis)
            return Response(serializer.data)

        analyze_area_data.delay(area.id)

        return Response({"message": "Analysis task has been started. Please check back later for the result."}, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=['get'], url_path='latest-analysis')
    def latest_analysis(self, request, pk=None):
        try:
            area = Area.objects.get(pk=pk)
        except Area.DoesNotExist:
            return Response({"error": "Area not found"}, status=status.HTTP_404_NOT_FOUND)

        latest_analysis = self.get_queryset().filter(area=area).first()

        if not latest_analysis:
            return Response({"message": "No analysis found for this area."}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(latest_analysis)
        return Response(serializer.data)

    # 新增：按区域ID分页获取历史分析列表（默认10条，可用?limit=20控制）
    @action(detail=False, methods=['get'], url_path='areas/(?P<area_id>[^/.]+)/analyses')
    def analyses_by_area(self, request, area_id=None):
        try:
            area = Area.objects.get(pk=area_id)
        except Area.DoesNotExist:
            return Response({"error": "Area not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            limit = int(request.query_params.get('limit', 10))
        except ValueError:
            limit = 10

        qs = self.get_queryset().filter(area=area).order_by('-timestamp')[:max(1, min(limit, 100))]
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


class UserRecommendationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = UserRecommendation.objects.all().order_by('-timestamp')
    serializer_class = UserRecommendationSerializer
    
    @action(detail=False, methods=['get'], url_path='user/(?P<user_id>[^/.]+)')
    def get_user_recommendations(self, request, user_id=None):
        try:
            user = CustomUser.objects.get(pk=user_id)
        except CustomUser.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # 获取用户的最新推荐
        recommendations = self.get_queryset().filter(user=user).order_by('-timestamp')[:5]
        
        # 如果没有推荐或推荐较老，触发生成任务
        if not recommendations.exists() or recommendations.first().timestamp < timezone.now() - timedelta(days=1):
            generate_personalized_recommendations.delay()
            
            if not recommendations.exists():
                return Response({
                    "message": "正在为您生成个性化推荐，请稍后再试",
                    "status": "generating"
                }, status=status.HTTP_202_ACCEPTED)
        
        serializer = self.get_serializer(recommendations, many=True)
        return Response(serializer.data)


class AlertAnalysisViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AlertAnalysis.objects.all().order_by('-timestamp')
    serializer_class = AlertAnalysisSerializer
    
    @action(detail=False, methods=['get'], url_path='alert/(?P<alert_id>[^/.]+)')
    def get_alert_analysis(self, request, alert_id=None):
        try:
            alert = Alert.objects.get(pk=alert_id)
        except Alert.DoesNotExist:
            return Response({"error": "Alert not found"}, status=status.HTTP_404_NOT_FOUND)
        
        try:
            analysis = self.get_queryset().get(alert=alert)
        except AlertAnalysis.DoesNotExist:
            # 如果没有分析，触发分析任务
            analyze_alert.delay(alert.id)
            return Response({
                "message": "正在为该告警生成分析，请稍后再试",
                "status": "analyzing"
            }, status=status.HTTP_202_ACCEPTED)
        
        serializer = self.get_serializer(analysis)
        return Response(serializer.data)


class AreaUsagePatternViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AreaUsagePattern.objects.all()
    serializer_class = AreaUsagePatternSerializer
    
    @action(detail=False, methods=['get'], url_path='area/(?P<area_id>[^/.]+)')
    def get_area_pattern(self, request, area_id=None):
        try:
            area = Area.objects.get(pk=area_id)
        except Area.DoesNotExist:
            return Response({"error": "Area not found"}, status=status.HTTP_404_NOT_FOUND)
        
        try:
            pattern = self.get_queryset().get(area=area)
            
            # 如果分析过期（超过7天），触发更新
            if pattern.last_updated < timezone.now() - timedelta(days=7):
                generate_area_usage_pattern.delay(area.id)
                return Response({
                    "message": "区域使用模式分析正在更新，返回当前可用数据",
                    "status": "updating",
                    "data": self.get_serializer(pattern).data
                })
            
            serializer = self.get_serializer(pattern)
            return Response(serializer.data)
            
        except AreaUsagePattern.DoesNotExist:
            # 如果没有分析，触发分析任务
            generate_area_usage_pattern.delay(area.id)
            return Response({
                "message": "正在为该区域生成使用模式分析，请稍后再试",
                "status": "generating"
            }, status=status.HTTP_202_ACCEPTED)


class GeneratedContentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = GeneratedContent.objects.all().order_by('-generated_at')
    serializer_class = GeneratedContentSerializer
    
    @action(detail=False, methods=['get'], url_path='area/(?P<area_id>[^/.]+)/notices')
    def get_area_notices(self, request, area_id=None):
        try:
            area = Area.objects.get(pk=area_id)
        except Area.DoesNotExist:
            return Response({"error": "Area not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # 获取区域的公告
        notices = self.get_queryset().filter(
            content_type='notice',
            related_area=area
        ).order_by('-generated_at')[:5]
        
        serializer = self.get_serializer(notices, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'], url_path='generate/notice')
    def generate_notice(self, request):
        area_id = request.data.get('area_id')
        notice_type = request.data.get('notice_type', 'status')
        
        if not area_id:
            return Response({"error": "Area ID is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            area = Area.objects.get(pk=area_id)
        except Area.DoesNotExist:
            return Response({"error": "Area not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # 这里简化处理，直接生成公告
        # 实际应用中可能需要调用异步任务
        
        # 生成的公告示例
        if notice_type == "status":
            title = f"{area.name}状态通知"
            content = f"尊敬的用户，{area.name}目前状态良好，环境舒适。当前人流量适中，温度适宜。欢迎前来使用！"
        elif notice_type == "alert":
            title = f"{area.name}告警通知"
            content = f"注意：{area.name}区域检测到异常情况，请相关人员及时处理。"
        elif notice_type == "maintenance":
            title = f"{area.name}维护通知"
            content = f"{area.name}将于今日进行例行设备维护，可能会影响部分功能的使用。给您带来不便，敬请谅解。"
        else:
            title = f"{area.name}通知"
            content = f"这是关于{area.name}的通知。"
        
        # 创建生成内容记录
        generated_content = GeneratedContent.objects.create(
            content_type='notice',
            title=title,
            content=content,
            related_area=area,
            prompt_used=f"为{area.name}生成{notice_type}类型的公告"
        )
        
        serializer = self.get_serializer(generated_content)
        return Response(serializer.data)


class AgentChatView(APIView):
    async def post(self, request):
        user_message = request.data.get('message')
        chat_history = request.data.get('history', []) or []

        if not user_message:
            return Response({"error": "Message not provided"}, status=status.HTTP_400_BAD_REQUEST)

        # 统一SSE格式：每条消息以"data: "开头，以空行分隔；最后发送[DONE]
        async def stream_generator():
            try:
                async for chunk in get_agent_response(user_message, chat_history):
                    # chunk可能为字符串或结构化对象，统一转为JSON字符串，便于前端解析
                    data = chunk
                    if not isinstance(chunk, str):
                        data = json.dumps(chunk, ensure_ascii=False)
                    yield f"data: {data}\n\n"
            except Exception as e:
                # 简单错误透传，前端可据此提示
                err = json.dumps({"error": str(e)}, ensure_ascii=False)
                yield f"data: {err}\n\n"
            finally:
                yield "data: [DONE]\n\n"

        response = StreamingHttpResponse(stream_generator(), content_type='text/event-stream')
        # 可选：提升SSE兼容性
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'  # Nginx下禁用缓冲以实时推送
        return response