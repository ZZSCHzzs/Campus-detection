from django.db import models
from webapi.models import Area, CustomUser, Alert
from django.utils import timezone

class LLMAnalysis(models.Model):
    """存储LLM分析结果的模型"""
    area = models.ForeignKey(Area, on_delete=models.CASCADE, related_name='analyses', verbose_name="分析区域")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="分析时间")
    analysis_text = models.TextField(help_text="LLM生成的分析文本", verbose_name="分析文本")
    analysis_data = models.JSONField(null=True, blank=True, help_text="JSON格式的分析数据", verbose_name="分析数据")
    alert_status = models.BooleanField(default=False, help_text="是否有警报", verbose_name="警报状态")
    alert_message = models.TextField(null=True, blank=True, help_text="警报信息", verbose_name="警报信息")
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = "LLM分析"
        verbose_name_plural = "LLM分析"
        
    def __str__(self):
        return f"{self.area.name} 分析 - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"

# 新增：用户推荐记录
class UserRecommendation(models.Model):
    """存储对用户的区域推荐记录"""
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='recommendations', verbose_name="用户")
    area = models.ForeignKey(Area, on_delete=models.CASCADE, related_name='recommendations', verbose_name="推荐区域")
    score = models.FloatField(verbose_name="推荐分数")
    reason = models.TextField(verbose_name="推荐理由")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="推荐时间")
    clicked = models.BooleanField(default=False, verbose_name="是否点击")
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = "用户推荐"
        verbose_name_plural = "用户推荐"
        
    def __str__(self):
        return f"{self.user.username} - {self.area.name} - {self.score}"

# 新增：智能告警分析
class AlertAnalysis(models.Model):
    """告警智能分析和处理建议"""
    alert = models.OneToOneField(Alert, on_delete=models.CASCADE, related_name='ai_analysis', verbose_name="关联告警")
    analysis_text = models.TextField(verbose_name="分析内容")
    priority_score = models.FloatField(verbose_name="优先级分数", help_text="0-1之间，越高越紧急")
    handling_suggestions = models.TextField(verbose_name="处理建议")
    potential_causes = models.TextField(verbose_name="可能原因")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="分析时间")
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = "告警分析"
        verbose_name_plural = "告警分析"
        
    def __str__(self):
        return f"告警分析 - {self.alert.area.name} - {self.alert.alert_type}"

# 新增：区域使用模式
class AreaUsagePattern(models.Model):
    """区域使用的时间模式和特征"""
    area = models.OneToOneField(Area, on_delete=models.CASCADE, related_name='usage_pattern', verbose_name="区域")
    daily_pattern = models.JSONField(verbose_name="日内模式", help_text="24小时人流量模式")
    weekly_pattern = models.JSONField(verbose_name="周内模式", help_text="一周内不同日期的模式")
    peak_hours = models.JSONField(verbose_name="高峰时段")
    quiet_hours = models.JSONField(verbose_name="低谷时段")
    average_duration = models.FloatField(verbose_name="平均停留时间(分钟)", null=True, blank=True)
    typical_user_groups = models.TextField(verbose_name="典型用户群体", null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    
    class Meta:
        verbose_name = "区域使用模式"
        verbose_name_plural = "区域使用模式"
        
    def __str__(self):
        return f"{self.area.name} 使用模式"

# 新增：智能内容生成
class GeneratedContent(models.Model):
    """由AI生成的内容，如公告、摘要等"""
    CONTENT_TYPES = [
        ('notice', '公告'),
        ('summary', '数据摘要'),
        ('report', '分析报告'),
        ('alert', '告警通知')
    ]
    
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPES, verbose_name="内容类型")
    title = models.CharField(max_length=200, verbose_name="标题")
    content = models.TextField(verbose_name="内容")
    related_area = models.ForeignKey(Area, on_delete=models.CASCADE, null=True, blank=True, 
                                    related_name='generated_contents', verbose_name="相关区域")
    target_users = models.ManyToManyField(CustomUser, blank=True, related_name='received_contents', 
                                         verbose_name="目标用户")
    generated_at = models.DateTimeField(auto_now_add=True, verbose_name="生成时间")
    published = models.BooleanField(default=False, verbose_name="是否已发布")
    prompt_used = models.TextField(verbose_name="使用的提示词", null=True, blank=True)
    
    class Meta:
        ordering = ['-generated_at']
        verbose_name = "生成内容"
        verbose_name_plural = "生成内容"
        
    def __str__(self):
        return f"{self.get_content_type_display()} - {self.title}"