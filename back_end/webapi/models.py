from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.utils import timezone

class HardwareNode(models.Model):
    name = models.CharField(max_length=100, verbose_name="节点名称")
    detected_count = models.IntegerField(default=0, verbose_name="检测结果")
    terminal = models.ForeignKey('ProcessTerminal', on_delete=models.CASCADE, verbose_name="终端")
    status = models.BooleanField(default=False, verbose_name="状态")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    description = models.TextField(blank=True, verbose_name="描述")
    temperature = models.FloatField(null=True, blank=True, verbose_name="温度")
    humidity = models.FloatField(null=True, blank=True, verbose_name="湿度")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "硬件节点"
        verbose_name_plural = "硬件节点"


class ProcessTerminal(models.Model):
    name = models.CharField(max_length=100, default='终端')
    status = models.BooleanField(default=False)
    last_active = models.DateTimeField(null=True, blank=True)
    
    # 终端性能状态
    cpu_usage = models.FloatField(default=0)
    memory_usage = models.FloatField(default=0)
    disk_usage = models.FloatField(default=0, verbose_name="磁盘使用率")
    disk_free = models.BigIntegerField(default=0, verbose_name="可用磁盘空间(字节)")
    disk_total = models.BigIntegerField(default=0, verbose_name="总磁盘空间(字节)")
    memory_available = models.BigIntegerField(default=0, verbose_name="可用内存(字节)")
    memory_total = models.BigIntegerField(default=0, verbose_name="总内存(字节)")
    co2_level = models.IntegerField(default=-1, verbose_name="CO2浓度(ppm)")
    co2_status = models.CharField(max_length=20, default="未连接", verbose_name="CO2传感器状态")
    
    # 检测服务状态
    model_loaded = models.BooleanField(default=False)
    push_running = models.BooleanField(default=False)
    pull_running = models.BooleanField(default=False)
    
    # 终端配置
    mode = models.CharField(max_length=10, default='both', choices=[
        ('pull', '拉取模式'),
        ('push', '接收模式'),
        ('both', '双模式')
    ])
    interval = models.FloatField(default=5.0)
    camera_config = models.JSONField(default=dict, blank=True)
    save_image = models.BooleanField(default=True)
    preload_model = models.BooleanField(default=True)
    co2_enabled = models.BooleanField(default=True, verbose_name="启用CO2传感器")
    co2_read_interval = models.IntegerField(default=30, verbose_name="CO2读取间隔(秒)")
    node_config = models.JSONField(default=dict, blank=True, verbose_name="节点配置")

    # 节点状态
    nodes = models.JSONField(default=dict, blank=True)

    # 系统状态
    system_uptime = models.IntegerField(default=0, verbose_name="系统运行时间", blank=True, null=True)
    frame_rate = models.FloatField(default=0, verbose_name="帧率", blank=True, null=True)
    total_frames = models.IntegerField(default=0, verbose_name="总帧数", blank=True, null=True)
    terminal_id = models.IntegerField(default=1, verbose_name="终端ID")
    
    # 最后检测信息
    last_detection = models.JSONField(default=dict, blank=True, verbose_name="最后检测信息")

    def update_status(self, status_data):
        # 更新状态字段
        if 'model_loaded' in status_data:
            self.model_loaded = status_data['model_loaded']
        # 更新其他字段...
        self.last_active = timezone.now()
        self.save()


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
    capacity = models.IntegerField(default=0, verbose_name="容量")

    def __str__(self):
        return f"{self.name} ({self.type.name} - {self.floor}F)"

    class Meta:
        verbose_name = "区域"
        verbose_name_plural = "区域"


class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('user', '普通用户'),
        ('staff', '工作人员'),
        ('admin', '管理员'),
    ]

    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default='user', verbose_name="角色")
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="电话")
    email = models.EmailField(blank=True, null=True, verbose_name="邮箱")
    register_time = models.DateTimeField(auto_now_add=True, verbose_name="注册时间")
    favorite_areas = models.ManyToManyField(Area, blank=True, verbose_name="收藏区域", related_name="favorite_areas")
    # 显式重写 groups 和 user_permissions 字段
    groups = models.ManyToManyField(
        Group,
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.',
        related_name="customuser_groups",  # 唯一的 related_name
        related_query_name="customuser",
    )
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name="customuser_permissions",  # 唯一的 related_name
        related_query_name="customuser",
    )

    def __str__(self):
        return self.username

    class Meta:
        verbose_name = "用户"
        verbose_name_plural = "用户"

    def save(self, *args, **kwargs):
        # 根据 role 同步 is_staff 和 is_superuser
        if self.role == 'admin':
            self.is_staff = True
            self.is_superuser = True
        elif self.role == 'staff':
            self.is_staff = True
            self.is_superuser = False
        else:  # user
            self.is_staff = False
            self.is_superuser = False

        super().save(*args, **kwargs)


class HistoricalData(models.Model):
    area = models.ForeignKey('Area', on_delete=models.CASCADE, verbose_name="区域")
    detected_count = models.IntegerField(verbose_name="检测到的人数")
    timestamp = models.DateTimeField(verbose_name="检测时间")

    def __str__(self):
        return f"{self.area.name} - {self.timestamp}"

    class Meta:
        verbose_name = "历史数据"
        verbose_name_plural = "历史数据"


class TemperatureHumidityData(models.Model):
    area = models.ForeignKey('Area', on_delete=models.CASCADE, verbose_name="区域")
    temperature = models.FloatField(null=True, blank=True, verbose_name="温度(°C)")
    humidity = models.FloatField(null=True, blank=True, verbose_name="湿度(%)")
    timestamp = models.DateTimeField(verbose_name="记录时间")

    def __str__(self):
        return f"{self.area.name} - 温湿度 - {self.timestamp}"

    class Meta:
        verbose_name = "温湿度数据"
        verbose_name_plural = "温湿度数据"
        ordering = ['-timestamp']


class CO2Data(models.Model):
    terminal = models.ForeignKey('ProcessTerminal', on_delete=models.CASCADE, verbose_name="终端")
    co2_level = models.IntegerField(verbose_name="CO2浓度(ppm)")
    timestamp = models.DateTimeField(verbose_name="记录时间")

    def __str__(self):
        return f"{self.terminal.name} - CO2:{self.co2_level}ppm - {self.timestamp}"

    class Meta:
        verbose_name = "CO2数据"
        verbose_name_plural = "CO2数据"
        ordering = ['-timestamp']


class Alert(models.Model):
    GRADE_CHOICES = [
        (0, '普通'),
        (1, '注意'),
        (2, '警告'),
        (3, '严重'),
    ]
    TYPE_CHOICES = [
        ('fire', '火灾'),
        ('guard', '安保'),
        ('crowd', '人群聚集'),
        ('health', '生命危急'),
        ('other', '其他'),
        ]

    area = models.ForeignKey('Area', on_delete=models.CASCADE, verbose_name="区域")
    grade = models.IntegerField(default=0, verbose_name="告警等级", choices=GRADE_CHOICES)
    alert_type = models.CharField(max_length=100, verbose_name="告警类型", choices=TYPE_CHOICES)
    publicity = models.BooleanField(default=True, verbose_name="是否公开")
    message = models.TextField(verbose_name="告警信息")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="告警时间")
    solved = models.BooleanField(default=False, verbose_name="是否已处理")


    def __str__(self):
        return f"{self.alert_type} - {self.area.name} - {self.timestamp}"

    class Meta:
        verbose_name = "告警"
        verbose_name_plural = "告警"


class Notice(models.Model):
    title = models.CharField(max_length=200, verbose_name="公告标题")
    content = models.TextField(verbose_name="公告内容")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="发布时间")
    related_areas = models.ManyToManyField(Area, blank=True, verbose_name="相关区域", related_name="notices")
    outdated = models.BooleanField(default=False, verbose_name="是否过期")
    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "公告"
        verbose_name_plural = "公告"