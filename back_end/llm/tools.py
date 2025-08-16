import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from django.utils import timezone
from django.db.models import Q, Max, Min, Avg, Count

from webapi.models import Area, HardwareNode, ProcessTerminal, Alert, HistoricalData, TemperatureHumidityData, CO2Data, Notice

from .utils import run_llm_with_retry
from .prompts import get_device_status_prompt


# 模糊搜索和匹配工具

def fuzzy_search_areas(query: str, category: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    基于查询词模糊搜索区域
    支持区域名称、建筑名称、楼层等关键词
    可选：按建筑类型(category)过滤，如 'library'/'study'/'cafeteria' 等
    """
    if not query.strip():
        return []
    
    query = query.strip().lower()
    areas = Area.objects.filter(id__lt=20).select_related('type', 'bound_node').all()
    matches = []
    
    for area in areas:
        # 若指定了类型过滤且不匹配，跳过
        if category and getattr(area.type, "category", None) != category:
            continue

        score = 0
        # 区域名称匹配
        if query in area.name.lower():
            score += 10
        # 建筑名称匹配
        if query in area.type.name.lower():
            score += 8
        # 楼层匹配
        if str(area.floor) in query or f"楼" in query:
            try:
                floor_in_query = int(''.join(filter(str.isdigit, query)))
                if floor_in_query == area.floor:
                    score += 5
            except ValueError:
                pass
        # 容量相关匹配
        if any(word in query for word in ["大", "小", "空间"]):
            if area.capacity > 100 and "大" in query:
                score += 3
            elif area.capacity < 50 and "小" in query:
                score += 3
        
        if score > 0:
            matches.append({
                "id": area.id,
                "name": area.name,
                "building": area.type.name,
                "building_id": area.type_id,
                "floor": area.floor,
                "capacity": area.capacity,
                "score": score,
                "current_count": area.bound_node.detected_count if area.bound_node else 0
            })
    
    # 按匹配分数排序
    matches.sort(key=lambda x: x['score'], reverse=True)
    return matches[:10]  # 返回前10个匹配结果


def fuzzy_search_buildings(query: str) -> List[Dict[str, Any]]:
    """基于查询词模糊搜索建筑"""
    if not query.strip():
        return []
    
    query = query.strip().lower()
    # 从Area关联获取建筑信息
    from webapi.models import Building
    buildings = Building.objects.all()
    matches = []
    
    for building in buildings:
        score = 0
        if query in building.name.lower():
            score += 10
        # 简单关键词匹配
        if any(word in building.name.lower() for word in query.split()):
            score += 5
            
        if score > 0:
            area_count = Area.objects.filter(type=building).count()
            matches.append({
                "id": building.id,
                "name": building.name,
                "area_count": area_count,
                "score": score
            })
    
    matches.sort(key=lambda x: x['score'], reverse=True)
    return matches[:5]


def fuzzy_search_terminals(query: str) -> List[Dict[str, Any]]:
    """基于查询词模糊搜索终端"""
    if not query.strip():
        return []
    
    query = query.strip().lower()
    terminals = ProcessTerminal.objects.all()
    matches = []
    
    for terminal in terminals:
        score = 0
        if query in terminal.name.lower():
            score += 10
        # ID匹配
        if str(terminal.terminal_id) in query:
            score += 8
        # 状态匹配
        if terminal.status and any(word in query for word in ["在线", "online", "正常"]):
            score += 3
        elif not terminal.status and any(word in query for word in ["离线", "offline", "故障"]):
            score += 3
            
        if score > 0:
            matches.append({
                "id": terminal.terminal_id,
                "name": terminal.name,
                "status": "online" if terminal.status else "offline",
                "score": score
            })
    
    matches.sort(key=lambda x: x['score'], reverse=True)
    return matches[:5]


# 基础数据工具

def get_area_status(area_id: int) -> Dict[str, Any]:
    """获取指定区域的综合状态数据"""
    try:
        area = Area.objects.get(id=area_id)
    except Area.DoesNotExist:
        return {"error": "area_not_found", "area_id": area_id}

    # 从绑定的硬件节点获取人流数据
    bound_node = area.bound_node
    crowd = {
        "current": bound_node.detected_count,
        "capacity": area.capacity,
        "ratio": round((bound_node.detected_count / float(area.capacity)) if area.capacity > 0 else 0, 2)
    }

    # 从硬件节点获取温湿度数据
    env = {
        "temperature": bound_node.temperature,
        "humidity": bound_node.humidity,
    }
    
    # 从终端获取CO2数据
    terminal = bound_node.terminal
    env["co2"] = terminal.co2_level if terminal.co2_level > 0 else None

    # 获取该区域的告警信息
    alerts_raw = list(Alert.objects.filter(area=area).values("id", "grade", "alert_type", "message", "timestamp")[:5])
    # 将 datetime 转为可序列化的 ISO 字符串
    alerts = []
    for a in alerts_raw:
        a = dict(a)
        ts = a.get("timestamp")
        if ts is not None:
            try:
                a["timestamp"] = ts.isoformat()
            except Exception:
                a["timestamp"] = str(ts)
        alerts.append(a)

    return {
        "area": {
            "id": area.id,
            "name": area.name,
            "building": area.type.name,
            "building_id": area.type_id,
            "floor": area.floor,
            "capacity": area.capacity,
        },
        "crowd": crowd,
        "environment": env,
        "alerts": alerts
    }


def get_suggested_areas(limit: int = 5, category: Optional[str] = None) -> List[Dict[str, Any]]:
    """根据实际人流负荷推荐区域，可选按建筑类型过滤"""
    qs = Area.objects.filter(id__lt=20).select_related('bound_node', 'type')
    if category:
        qs = qs.filter(type__category=category)

    suggestions = []
    for area in qs.all():
        current_count = area.bound_node.detected_count
        capacity = area.capacity
        load_ratio = round((current_count / float(capacity)) if capacity > 0 else 0, 2)
        suggestions.append({
            "id": area.id,
            "name": area.name,
            "building": area.type.name,
            "building_id": area.type_id,
            "floor": area.floor,
            "capacity": area.capacity,
            "current_count": current_count,
            "load_ratio": load_ratio,
        })
    
    suggestions.sort(key=lambda x: x['current_count'])
    return suggestions[:limit]


def get_terminal_status(terminal_id: int) -> Dict[str, Any]:
    """从ProcessTerminal模型获取真实终端状态（不新增字段）"""
    try:
        terminal = ProcessTerminal.objects.get(terminal_id=terminal_id)
    except ProcessTerminal.DoesNotExist:
        return {"error": "terminal_not_found", "terminal_id": terminal_id}
    
    # 计算内存与磁盘（GB）
    mem_total_gb = round(terminal.memory_total / (1024**3), 1) if terminal.memory_total else 0.0
    mem_used_gb = round((terminal.memory_total - terminal.memory_available) / (1024**3), 1) if (terminal.memory_total and terminal.memory_available is not None) else 0.0

    disk_total_gb = round(terminal.disk_total / (1024**3), 1) if terminal.disk_total else 0.0
    disk_used_gb = round((terminal.disk_total - terminal.disk_free) / (1024**3), 1) if (terminal.disk_total and terminal.disk_free is not None) else 0.0

    terminal_data = {
        "id": terminal.terminal_id,
        "name": terminal.name,
        "cpu": {"usage": terminal.cpu_usage / 100.0},
        "memory": {"used": mem_used_gb, "total": mem_total_gb},
        "disk_usage": {"used": disk_used_gb, "total": disk_total_gb},
        "status": "online" if terminal.status else "offline",
    }

    nodes = []
    for node in HardwareNode.objects.filter(terminal=terminal):
        nodes.append({
            "id": node.id,
            "type": "detection_node",
            "status": "online" if node.status else "offline",
        })

    return {"terminal": terminal_data, "nodes": nodes}


# 结合LLM的工具
async def summarize_terminal_status(terminal_id: int) -> str:
    """调用LLM生成终端状态摘要"""
    status = get_terminal_status(terminal_id)
    if "error" in status:
        return f"终端 {terminal_id} 不存在或无法访问"
    
    prompt = get_device_status_prompt(
        device_info=json.dumps(status.get('terminal'), ensure_ascii=False, indent=2),
        performance_metrics=json.dumps({
            "cpu": status['terminal']['cpu'],
            "memory": status['terminal']['memory'],
            "disk": status['terminal']['disk_usage']
        }, ensure_ascii=False, indent=2),
        runtime_status=json.dumps({
            "nodes": status.get('nodes', [])
        }, ensure_ascii=False, indent=2)
    )
    # 构造消息格式供 run_llm_with_retry
    from langchain.schema import SystemMessage, HumanMessage
    messages = [
        SystemMessage(content="你是设备状态汇总专家，基于提供的数据生成简洁、结构化且可操作的摘要。务必避免臆测。"),
        HumanMessage(content=prompt)
    ]
    return await run_llm_with_retry(messages, temperature=0.2, model_type="analysis")


def get_area_extremes(area_id: int, hours: int = 24) -> Dict[str, Any]:
    """获取指定时间窗口内该区域的人流极值与时间点（基于HistoricalData）"""
    try:
        area = Area.objects.get(id=area_id)
    except Area.DoesNotExist:
        return {"error": "area_not_found", "area_id": area_id}

    since = timezone.now() - timedelta(hours=hours)
    qs = HistoricalData.objects.filter(area=area, timestamp__gte=since)
    if not qs.exists():
        return {
            "area_id": area_id,
            "window_hours": hours,
            "min": None,
            "max": None
        }

    min_obj = qs.order_by("detected_count", "timestamp").first()
    max_obj = qs.order_by("-detected_count", "timestamp").first()
    return {
        "area_id": area_id,
        "window_hours": hours,
        "min": {"count": min_obj.detected_count, "timestamp": min_obj.timestamp.isoformat()},
        "max": {"count": max_obj.detected_count, "timestamp": max_obj.timestamp.isoformat()},
    }


def get_area_trend(area_id: int, hours: int = 6, interval_minutes: int = 30) -> List[Dict[str, Any]]:
    """返回时间序列趋势（简化：按interval聚合均值），用于画趋势或给LLM做分析"""
    try:
        area = Area.objects.get(id=area_id)
    except Area.DoesNotExist:
        return []

    since = timezone.now() - timedelta(hours=hours)
    qs = HistoricalData.objects.filter(area=area, timestamp__gte=since).order_by("timestamp")
    # 简化实现：直接返回原始序列（不虚构），前端/LLM可自行聚合
    return [{
        "timestamp": h.timestamp.isoformat(),
        "detected_count": h.detected_count
    } for h in qs]


def get_recent_alerts(area_id: int | None = None, limit: int = 10) -> List[Dict[str, Any]]:
    """获取最新告警列表（不造字段）"""
    qs = Alert.objects.all().order_by("-timestamp")
    if area_id:
        qs = qs.filter(area_id=area_id)
    data = []
    for a in qs[:limit]:
        data.append({
            "id": a.id,
            "area_id": a.area_id,
            "grade": a.grade,
            "alert_type": a.alert_type,
            "message": a.message,
            "timestamp": a.timestamp.isoformat(),
            "solved": a.solved,
        })
    return data


def get_environment_snapshots(area_id: int, hours: int = 6, limit: int = 50) -> List[Dict[str, Any]]:
    """获取温湿度历史切片（基于TemperatureHumidityData）"""
    try:
        area = Area.objects.get(id=area_id)
    except Area.DoesNotExist:
        return []
    since = timezone.now() - timedelta(hours=hours)
    qs = TemperatureHumidityData.objects.filter(area=area, timestamp__gte=since).order_by("-timestamp")[:limit]
    return [{
        "temperature": r.temperature,
        "humidity": r.humidity,
        "timestamp": r.timestamp.isoformat(),
    } for r in qs]


def get_notices(area_id: int | None = None, limit: int = 10) -> List[Dict[str, Any]]:
    """获取公告（Notice），结合区域多对多关系"""
    qs = Notice.objects.all().order_by("-timestamp")
    if area_id:
        qs = qs.filter(related_areas__id=area_id)
    results = []
    for n in qs.distinct()[:limit]:
        results.append({
            "id": n.id,
            "title": n.title,
            "content": n.content,
            "timestamp": n.timestamp.isoformat(),
            "related_area_ids": list(n.related_areas.values_list("id", flat=True)),
            "outdated": n.outdated,
        })
    return results


def get_terminal_latest_co2(terminal_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """获取终端CO2历史记录切片（基于CO2Data）"""
    qs = CO2Data.objects.filter(terminal__terminal_id=terminal_id).order_by("-timestamp")[:limit]
    return [{
        "co2_level": r.co2_level,
        "timestamp": r.timestamp.isoformat(),
    } for r in qs]


# 资源导航工具

def get_campus_resources(query: str = "") -> List[Dict[str, Any]]:
    """
    根据用户查询关键词返回相关的校园服务资源
    支持教务、图书馆、运动、校园卡等服务的链接导航
    """
    # 校园服务资源映射
    campus_services = [
        {
            "name": "校内新闻",
            "description": "哈工大今日校园新闻、通知公告",
            "url": "http://today.hit.edu.cn",
            "keywords": ["新闻", "通知", "公告", "校内", "今日", "资讯", "消息"]
        },
        {
            "name": "本科生教务系统",
            "description": "本科生课程安排、成绩查询、选课系统",
            "url": "http://jwts.hit.edu.cn",
            "keywords": ["教务", "本科", "选课", "成绩", "课程", "课表", "学分"]
        },
        {
            "name": "研究生管理系统",
            "description": "研究生培养、学位管理、导师选择",
            "url": "http://yjsgl.hit.edu.cn/",
            "keywords": ["研究生", "导师", "学位", "培养", "毕业", "论文", "答辩"]
        },
        {
            "name": "学校门户平台",
            "description": "统一身份认证、综合信息门户",
            "url": "http://i.hit.edu.cn",
            "keywords": ["门户", "登录", "认证", "统一", "平台", "首页"]
        },
        {
            "name": "IVPN校外访问",
            "description": "校外访问校内资源的VPN服务",
            "url": "http://i-hit-edu-cn.ivpn.hit.edu.cn",
            "keywords": ["vpn", "校外", "远程", "访问", "网络", "连接"]
        },
        {
            "name": "学工系统",
            "description": "学生事务管理、奖助学金、违纪处理",
            "url": "https://xg.hit.edu.cn/xs/mh",
            "keywords": ["学工", "学生", "奖学金", "助学金", "事务", "管理", "违纪"]
        },
        {
            "name": "校园卡服务",
            "description": "校园卡充值、消费查询、挂失补办",
            "url": "http://xyk.hit.edu.cn",
            "keywords": ["校园卡", "充值", "消费", "余额", "挂失", "补办", "食堂"]
        },
        {
            "name": "运动场地预约",
            "description": "体育场馆、运动场地在线预约",
            "url": "http://venue-book.hit.edu.cn:8080/",
            "keywords": ["运动", "体育", "场地", "预约", "健身", "球场", "游泳"]
        },
        {
            "name": "图书馆预约",
            "description": "图书馆座位预约、书籍查询、续借",
            "url": "http://ic.lib.hit.edu.cn/",
            "keywords": ["图书馆", "座位", "预约", "借书", "续借", "查询", "自习"]
        }
    ]
    
    if not query.strip():
        # 返回所有服务
        return campus_services
    
    # 基于关键词匹配相关服务
    query_lower = query.lower().strip()
    matching_services = []
    
    for service in campus_services:
        score = 0
        # 检查服务名称匹配
        if query_lower in service["name"].lower():
            score += 10
        # 检查描述匹配
        if query_lower in service["description"].lower():
            score += 5
        # 检查关键词匹配
        for keyword in service["keywords"]:
            if keyword in query_lower or query_lower in keyword:
                score += 3
        
        if score > 0:
            service_copy = service.copy()
            service_copy["relevance_score"] = score
            matching_services.append(service_copy)
    
    # 按相关性排序
    matching_services.sort(key=lambda x: x["relevance_score"], reverse=True)
    return matching_services[:5]  # 返回最相关的5个服务


def get_general_campus_info() -> Dict[str, Any]:
    """
    提供校园基础信息和AI助手身份说明
    用于普通对话场景的自我介绍
    """
    return {
        "assistant_name": "云小瞻",
        "assistant_role": "智慧校园AI助手",
        "capabilities": [
            "校园区域人流查询与分析",
            "环境数据监测（温湿度、CO2）",
            "校园资源导航与链接提供",
            "设备状态监控与告警",
            "校园服务信息查询",
            "日常问题解答"
        ],
        "campus_name": "哈尔滨工业大学",
        "system_description": "智慧校园空间感知调控系统",
        "service_scope": "为师生提供校园信息查询、数据分析与智能建议"
    }


__all__ = [
    # 模糊搜索工具
    "fuzzy_search_areas",
    "fuzzy_search_buildings", 
    "fuzzy_search_terminals",
    # 基础数据工具
    "get_area_status",
    "get_suggested_areas",
    "get_terminal_status",
    "summarize_terminal_status",
    # 扩展工具
    "get_area_extremes",
    "get_area_trend",
    "get_recent_alerts",
    "get_environment_snapshots",
    "get_notices",
    "get_terminal_latest_co2",
    # 新增：资源导航工具
    "get_campus_resources",
    "get_general_campus_info",
]