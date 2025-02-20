from django.db import models
from django.contrib.auth.models import AbstractUser


class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('user', '普通用户'),
        ('admin', '管理员'),
    ]

    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default='user', verbose_name="角色")
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="电话")
    email = models.EmailField(blank=True, null=True, verbose_name="邮箱")
    register_time = models.DateTimeField(auto_now_add=True, verbose_name="注册时间")


    def __str__(self):
        return self.username

    class Meta:
        verbose_name = "用户"
        verbose_name_plural = "用户"


class HardwareNode(models.Model):
    name = models.CharField(max_length=100, verbose_name="节点名称")
    detected_count = models.IntegerField(default=0, verbose_name="检测结果")
    terminal = models.ForeignKey('ProcessTerminal', on_delete=models.CASCADE, verbose_name="终端")
    status = models.BooleanField(default=False, verbose_name="状态")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    description = models.TextField(blank=True, verbose_name="描述")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "硬件节点"
        verbose_name_plural = "硬件节点"


class ProcessTerminal(models.Model):
    name = models.CharField(max_length=100, verbose_name="终端名称")
    status = models.BooleanField(default=False, verbose_name="状态")


class Building(models.Model):
    name = models.CharField(max_length=100, verbose_name="建筑名称")
    description = models.TextField(blank=True, verbose_name="描述")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "建筑"
        verbose_name_plural = "建筑"


class Area(models.Model):
    name = models.CharField(max_length=100, verbose_name="区域名称")
    bound_node = models.ForeignKey(HardwareNode, on_delete=models.CASCADE, verbose_name="绑定节点")
    description = models.TextField(blank=True, verbose_name="描述")
    type = models.ForeignKey(Building, on_delete=models.CASCADE, verbose_name="所属建筑")
    floor = models.IntegerField(default=0, verbose_name="楼层")

    def __str__(self):
        return f"{self.name} ({self.type.name} - {self.floor}F)"

    class Meta:
        verbose_name = "区域"
        verbose_name_plural = "区域"


class HistoricalData(models.Model):
    area = models.ForeignKey('Area', on_delete=models.CASCADE, verbose_name="区域")
    detected_count = models.IntegerField(verbose_name="检测到的人数")
    timestamp = models.DateTimeField(verbose_name="检测时间")

    def __str__(self):
        return f"{self.area.name} - {self.timestamp}"

    class Meta:
        verbose_name = "历史数据"
        verbose_name_plural = "历史数据"




