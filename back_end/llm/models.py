from django.db import models
from django.contrib.auth import get_user_model
from webapi.models import Area, Alert

User = get_user_model()


class LLMAnalysis(models.Model):
    """LLM分析结果存储"""
    area = models.ForeignKey(Area, on_delete=models.CASCADE, related_name='llm_analyses')
    timestamp = models.DateTimeField(auto_now_add=True)
    analysis_text = models.TextField(help_text="LLM生成的分析文本")
    analysis_data = models.TextField(blank=True, null=True, help_text="JSON格式的分析数据")
    alert_status = models.CharField(max_length=20, default='normal', 
                                   choices=[
                                       ('normal', '正常'),
                                       ('warning', '警告'),
                                       ('critical', '严重')
                                   ])
    alert_message = models.TextField(blank=True, null=True, help_text="告警信息")
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = "LLM分析结果"
        verbose_name_plural = "LLM分析结果"


class UserRecommendation(models.Model):
    """用户推荐记录"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recommendations')
    area = models.ForeignKey(Area, on_delete=models.CASCADE, related_name='user_recommendations')
    score = models.FloatField(help_text="推荐分数(0-1)")
    reason = models.TextField(help_text="推荐理由")
    timestamp = models.DateTimeField(auto_now_add=True)
    clicked = models.BooleanField(default=False, help_text="用户是否点击了该推荐")
    
    class Meta:
        ordering = ['-timestamp']
        unique_together = ['user', 'area', 'timestamp']
        verbose_name = "用户推荐"
        verbose_name_plural = "用户推荐"


class AlertAnalysis(models.Model):
    """告警智能分析"""
    alert = models.OneToOneField(Alert, on_delete=models.CASCADE, related_name='ai_analysis')
    analysis_text = models.TextField(help_text="LLM生成的分析文本")
    priority_score = models.FloatField(help_text="优先级分数(0-1)")
    handling_suggestions = models.TextField(help_text="处理建议")
    potential_causes = models.TextField(help_text="可能原因分析")
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = "告警分析"
        verbose_name_plural = "告警分析"


class AreaUsagePattern(models.Model):
    """区域使用模式"""
    area = models.OneToOneField(Area, on_delete=models.CASCADE, related_name='usage_pattern')
    daily_pattern = models.JSONField(help_text="日内使用模式，按小时统计")
    weekly_pattern = models.JSONField(help_text="周内使用模式，按星期统计")
    peak_hours = models.JSONField(help_text="高峰时段")
    quiet_hours = models.JSONField(help_text="低峰时段")
    average_duration = models.FloatField(help_text="平均使用时长(分钟)")
    typical_user_groups = models.TextField(help_text="典型用户群体")
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "区域使用模式"
        verbose_name_plural = "区域使用模式"


class GeneratedContent(models.Model):
    """AI生成内容"""
    CONTENT_TYPE_CHOICES = [
        ('notice', '公告'),
        ('report', '报告'),
        ('summary', '摘要'),
        ('recommendation', '推荐'),
    ]
    
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPE_CHOICES)
    title = models.CharField(max_length=200)
    content = models.TextField()
    related_area = models.ForeignKey(Area, on_delete=models.CASCADE, null=True, blank=True, 
                                   related_name='generated_contents')
    prompt_used = models.TextField(help_text="使用的提示词")
    generated_at = models.DateTimeField(auto_now_add=True)
    published = models.BooleanField(default=False, help_text="是否已发布")
    
    class Meta:
        ordering = ['-generated_at']
        verbose_name = "AI生成内容"
        verbose_name_plural = "AI生成内容"