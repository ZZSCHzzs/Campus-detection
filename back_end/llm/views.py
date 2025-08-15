from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.views import View
from django.http import StreamingHttpResponse
from django.utils import timezone
from datetime import timedelta
from asgiref.sync import async_to_sync
import json
import logging
import asyncio

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
from .utils import get_model_info


class LLMAnalysisViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LLMAnalysis.objects.all().order_by('-timestamp')
    serializer_class = LLMAnalysisSerializer

    @action(detail=True, methods=['post'], url_path='analyze')
    def analyze_area(self, request, pk=None):
        try:
            area = Area.objects.get(pk=pk)
        except Area.DoesNotExist:
            return Response({"error": "Area not found"}, status=status.HTTP_404_NOT_FOUND)

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
        
        recommendations = self.get_queryset().filter(user=user).order_by('-timestamp')[:5]
        
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
        
        generated_content = GeneratedContent.objects.create(
            content_type='notice',
            title=title,
            content=content,
            related_area=area,
            prompt_used=f"为{area.name}生成{notice_type}类型的公告"
        )
        
        serializer = self.get_serializer(generated_content)
        return Response(serializer.data)


class ModelInfoView(View):
    async def get(self, request, *args, **kwargs):
        """
        获取模型信息API，返回可用模型配置
        """
        model_info = get_model_info()
        return Response(model_info)


class AgentChatView(View):
    async def post(self, request, *args, **kwargs):
        body_bytes = request.body
        try:
            data = json.loads(body_bytes)
        except json.JSONDecodeError:
            return StreamingHttpResponse(
                json.dumps({"error": "Invalid JSON"}),
                status=400,
                content_type="application/json"
            )

        user_message = data.get("message")
        chat_history = data.get("history", []) or []
        model_type = data.get("model_type", "default")  # 提取模型类型，默认为default

        if not user_message:
            return StreamingHttpResponse(
                json.dumps({"error": "Message not provided"}),
                status=400,
                content_type="application/json"
            )

        async def stream_generator():
            try:
                async for chunk in get_agent_response(user_message, chat_history, model_type=model_type):
                    data_out = chunk if isinstance(chunk, str) else json.dumps(chunk, ensure_ascii=False)
                    yield f"data: {data_out}\n\n"
                    await asyncio.sleep(0)
            except Exception as e:
                import traceback
                traceback_str = traceback.format_exc()
                logging.error(f"Agent响应生成失败: {str(e)}\n{traceback_str}")
                yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
            finally:
                yield "data: [DONE]\n\n"
                await asyncio.sleep(0)

        # 创建响应对象并设置关键的流式传输头部
        response = StreamingHttpResponse(stream_generator(), content_type="text/event-stream")
        
        # 防止缓冲的关键头部
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate, no-transform'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        response['X-Accel-Buffering'] = 'no'  # 禁用nginx缓冲
        response['Connection'] = 'keep-alive'
        
        return response