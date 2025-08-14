from celery import shared_task
from django.conf import settings
from datetime import datetime, timedelta
import json
import logging
import asyncio
import pandas as pd
import numpy as np
from django.db.models import Avg, Count
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema import HumanMessage, SystemMessage

from webapi.models import Area, SensorData, SensorType, Alert, HistoricalData, CustomUser, TemperatureHumidityData
from .models import LLMAnalysis, AlertAnalysis, AreaUsagePattern, GeneratedContent, UserRecommendation

logger = logging.getLogger(__name__)

# 配置阈值和分析参数
ANALYSIS_CONFIG = {
    "crowd": {
        "warning_threshold": 80,  # 人流量警告阈值
        "critical_threshold": 120,  # 人流量严重阈值
        "timeframe_hours": 24,  # 分析最近24小时数据
    },
    "temperature": {
        "min_comfortable": 18,  # 最低舒适温度
        "max_comfortable": 26,  # 最高舒适温度
        "warning_low": 16,  # 低温警告阈值
        "warning_high": 28,  # 高温警告阈值
        "critical_low": 10,  # 低温严重阈值
        "critical_high": 32,  # 高温严重阈值
    },
    "humidity": {
        "min_comfortable": 40,  # 最低舒适湿度
        "max_comfortable": 60,  # 最高舒适湿度
        "warning_low": 30,  # 低湿度警告阈值
        "warning_high": 70,  # 高湿度警告阈值
    }
}

def get_crowd_data(area_id, hours=24):
    """获取区域历史人流量数据"""
    try:
        area = Area.objects.get(pk=area_id)
        # 使用HistoricalData查询人流量
        time_threshold = datetime.now() - timedelta(hours=hours)
        
        data = HistoricalData.objects.filter(
            area=area,
            timestamp__gte=time_threshold
        ).order_by('timestamp')
        
        return list(data.values('detected_count', 'timestamp'))
    except Area.DoesNotExist:
        logger.error(f"Area with id {area_id} not found")
        return []

def get_temperature_humidity_data(area_id, hours=24):
    """获取区域温湿度数据"""
    try:
        area = Area.objects.get(pk=area_id)
        time_threshold = datetime.now() - timedelta(hours=hours)
        
        data = TemperatureHumidityData.objects.filter(
            area=area,
            timestamp__gte=time_threshold
        ).order_by('timestamp')
        
        return list(data.values('temperature', 'humidity', 'timestamp'))
    except Area.DoesNotExist:
        logger.error(f"Area with id {area_id} not found")
        return []

def analyze_crowd_data(crowd_data):
    """分析人流量数据"""
    if not crowd_data:
        return {
            "status": "unknown",
            "message": "No crowd data available",
            "alert": False
        }
    
    # 提取当前值和历史统计
    current = crowd_data[-1]["detected_count"] if crowd_data else 0
    values = [item["detected_count"] for item in crowd_data]
    
    avg = sum(values) / len(values) if values else 0
    max_value = max(values) if values else 0
    min_value = min(values) if values else 0
    
    # 判断当前人流状态
    status = "normal"
    message = "Normal crowd levels"
    alert = False
    
    if current >= ANALYSIS_CONFIG["crowd"]["critical_threshold"]:
        status = "critical"
        message = "Critically high crowd level detected"
        alert = True
    elif current >= ANALYSIS_CONFIG["crowd"]["warning_threshold"]:
        status = "warning"
        message = "High crowd level detected"
        alert = True
    
    # 判断趋势
    trend = "stable"
    if len(values) >= 3:
        recent_avg = sum(values[-3:]) / 3
        earlier_avg = sum(values[:3]) / 3
        
        if recent_avg > earlier_avg * 1.2:
            trend = "increasing"
        elif recent_avg < earlier_avg * 0.8:
            trend = "decreasing"
    
    return {
        "current": current,
        "average": avg,
        "max": max_value,
        "min": min_value,
        "status": status,
        "message": message,
        "trend": trend,
        "alert": alert,
        "data_points": len(crowd_data)
    }

def analyze_temperature_humidity_data(temp_humidity_data):
    """分析温湿度数据"""
    if not temp_humidity_data:
        return {
            "temperature": {
                "status": "unknown",
                "message": "No temperature data available",
                "alert": False
            },
            "humidity": {
                "status": "unknown",
                "message": "No humidity data available",
                "alert": False
            }
        }
    
    # 提取温度数据
    temp_values = [item["temperature"] for item in temp_humidity_data if item["temperature"] is not None]
    humidity_values = [item["humidity"] for item in temp_humidity_data if item["humidity"] is not None]
    
    # 分析温度
    temp_analysis = {
        "status": "unknown",
        "message": "No temperature data available",
        "alert": False
    }
    
    if temp_values:
        current_temp = temp_values[-1]
        avg_temp = sum(temp_values) / len(temp_values)
        max_temp = max(temp_values)
        min_temp = min(temp_values)
        
        temp_analysis = {
            "current": current_temp,
            "average": avg_temp,
            "max": max_temp,
            "min": min_temp,
            "status": "comfortable",
            "message": "Temperature is within comfortable range",
            "alert": False
        }
        
        if current_temp <= ANALYSIS_CONFIG["temperature"]["critical_low"]:
            temp_analysis["status"] = "critical_low"
            temp_analysis["message"] = "Critically low temperature detected"
            temp_analysis["alert"] = True
        elif current_temp >= ANALYSIS_CONFIG["temperature"]["critical_high"]:
            temp_analysis["status"] = "critical_high"
            temp_analysis["message"] = "Critically high temperature detected"
            temp_analysis["alert"] = True
        elif current_temp <= ANALYSIS_CONFIG["temperature"]["warning_low"]:
            temp_analysis["status"] = "warning_low"
            temp_analysis["message"] = "Low temperature detected"
            temp_analysis["alert"] = True
        elif current_temp >= ANALYSIS_CONFIG["temperature"]["warning_high"]:
            temp_analysis["status"] = "warning_high"
            temp_analysis["message"] = "High temperature detected"
            temp_analysis["alert"] = True
    
    # 分析湿度
    humidity_analysis = {
        "status": "unknown",
        "message": "No humidity data available",
        "alert": False
    }
    
    if humidity_values:
        current_humidity = humidity_values[-1]
        avg_humidity = sum(humidity_values) / len(humidity_values)
        max_humidity = max(humidity_values)
        min_humidity = min(humidity_values)
        
        humidity_analysis = {
            "current": current_humidity,
            "average": avg_humidity,
            "max": max_humidity,
            "min": min_humidity,
            "status": "comfortable",
            "message": "Humidity is within comfortable range",
            "alert": False
        }
        
        if current_humidity <= ANALYSIS_CONFIG["humidity"]["warning_low"]:
            humidity_analysis["status"] = "warning_low"
            humidity_analysis["message"] = "Low humidity detected"
            humidity_analysis["alert"] = True
        elif current_humidity >= ANALYSIS_CONFIG["humidity"]["warning_high"]:
            humidity_analysis["status"] = "warning_high"
            humidity_analysis["message"] = "High humidity detected"
            humidity_analysis["alert"] = True
    
    return {
        "temperature": temp_analysis,
        "humidity": humidity_analysis
    }

async def generate_analysis_text(area_name, analysis_data):
    """使用LLM生成分析文本摘要"""
    system_prompt = """你是一个专业的校园环境分析专家。请根据提供的传感器数据分析信息，生成一份简明扼要的分析报告。
报告应包含以下要点：
1. 当前区域的总体状况概述
2. 人流量、温度、湿度等关键指标的分析
3. 任何需要注意的异常情况或警报
4. 基于数据的简短建议

使用专业但平易近人的语言，重点突出关键信息和任何需要立即关注的问题。"""

    human_prompt = f"""区域名称：{area_name}
分析数据：
```json
{json.dumps(analysis_data, ensure_ascii=False, indent=2)}
```

请根据以上数据生成一份简明的分析报告。"""

    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_prompt)
    ])
    
    llm = ChatOpenAI(
        temperature=0.3,
        openai_api_key=settings.OPENAI_API_KEY
    )
    
    response = await llm.agenerate([prompt.to_messages()])
    return response.generations[0][0].text

@shared_task
def analyze_area_data(area_id):
    """分析区域数据并生成报告"""
    try:
        area = Area.objects.get(pk=area_id)
        
        # 获取各类型数据
        crowd_data = get_crowd_data(area_id)
        temp_humidity_data = get_temperature_humidity_data(area_id)
        
        # 分析各类型数据
        crowd_analysis = analyze_crowd_data(crowd_data)
        env_analysis = analyze_temperature_humidity_data(temp_humidity_data)
        
        # 整合分析结果
        analysis_data = {
            "area": {
                "id": area.id,
                "name": area.name,
                "building": area.type.name,
                "floor": area.floor,
                "capacity": area.capacity
            },
            "timestamp": datetime.now().isoformat(),
            "crowd": crowd_analysis,
            "environment": env_analysis
        }
        
        # 确定整体警报状态
        alert_status = False
        alert_messages = []
        
        if crowd_analysis.get("alert"):
            alert_status = True
            alert_messages.append(crowd_analysis.get("message"))
        
        if env_analysis["temperature"].get("alert"):
            alert_status = True
            alert_messages.append(env_analysis["temperature"].get("message"))
        
        if env_analysis["humidity"].get("alert"):
            alert_status = True
            alert_messages.append(env_analysis["humidity"].get("message"))
        
        # 使用LLM生成分析文本
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        analysis_text = loop.run_until_complete(generate_analysis_text(area.name, analysis_data))
        loop.close()
        
        # 保存分析结果
        LLMAnalysis.objects.create(
            area=area,
            analysis_text=analysis_text,
            analysis_data=json.dumps(analysis_data, ensure_ascii=False),
            alert_status=alert_status,
            alert_message="; ".join(alert_messages) if alert_messages else None
        )
        
        logger.info(f"Completed analysis for area: {area.name}")
        return True
    
    except Exception as e:
        logger.error(f"Error analyzing area data: {str(e)}")
        return False

@shared_task
def analyze_alert(alert_id):
    """分析告警并生成处理建议"""
    try:
        alert = Alert.objects.get(pk=alert_id)
        
        # 检查是否已有分析
        if AlertAnalysis.objects.filter(alert=alert).exists():
            logger.info(f"Analysis already exists for alert {alert_id}")
            return True
        
        # 收集告警相关信息
        area = alert.area
        alert_type = alert.alert_type
        alert_grade = alert.grade
        alert_message = alert.message
        
        # 获取区域当前数据
        try:
            node = area.bound_node
            crowd_data = node.detected_count if node else None
            temp_data = node.temperature if node else None
            humidity_data = node.humidity if node else None
        except Exception as e:
            logger.warning(f"Could not get node data: {str(e)}")
            crowd_data = None
            temp_data = None
            humidity_data = None
        
        # 准备生成分析的提示
        alert_data = {
            "area_name": area.name,
            "area_building": area.type.name,
            "area_floor": area.floor,
            "alert_type": alert_type,
            "alert_grade": alert_grade,
            "alert_message": alert_message,
            "timestamp": alert.timestamp.isoformat(),
            "crowd_level": crowd_data,
            "temperature": temp_data,
            "humidity": humidity_data
        }
        
        # 使用LLM生成分析
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # 生成系统提示
        system_prompt = """你是一个专业的校园安全分析专家。请根据提供的告警信息，分析可能的原因、优先级，并提供处理建议。
你的分析应包含：
1. 可能的原因：分析导致告警的可能原因
2. 优先级评估：评估告警的紧急程度，给出0-1之间的优先级分数
3. 处理建议：提供具体的处理步骤和建议

请基于提供的数据进行分析，如果数据不足，可以指出需要收集哪些额外信息来做出更准确的判断。"""

        human_prompt = f"""告警信息：
```json
{json.dumps(alert_data, ensure_ascii=False, indent=2)}
```

请提供告警分析，包括可能原因、优先级评估和处理建议。"""

        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt)
        ])
        
        llm = ChatOpenAI(
            temperature=0.3,
            openai_api_key=settings.OPENAI_API_KEY
        )
        
        response = loop.run_until_complete(llm.agenerate([prompt.to_messages()]))
        analysis_text = response.generations[0][0].text
        loop.close()
        
        # 解析LLM响应，提取结构化信息
        # 这里使用简单的文本解析，实际应用中可能需要更复杂的处理
        
        # 确定优先级分数
        priority_score = alert_grade / 3.0  # 默认使用告警等级作为基础
        if "优先级" in analysis_text and "分数" in analysis_text:
            try:
                # 尝试从文本中提取优先级分数
                priority_text = analysis_text[analysis_text.find("优先级"):analysis_text.find("\n", analysis_text.find("优先级"))]
                if ":" in priority_text:
                    score_text = priority_text.split(":")[1].strip()
                    # 提取数字
                    import re
                    score_match = re.search(r"0\.\d+|\d+\.\d+|\d+", score_text)
                    if score_match:
                        extracted_score = float(score_match.group())
                        if 0 <= extracted_score <= 1:
                            priority_score = extracted_score
            except Exception as e:
                logger.warning(f"Error parsing priority score: {str(e)}")
        
        # 提取可能原因和处理建议
        causes_section = ""
        suggestions_section = ""
        
        if "可能原因" in analysis_text:
            causes_start = analysis_text.find("可能原因")
            next_section = analysis_text.find("优先级", causes_start)
            if next_section == -1:
                next_section = analysis_text.find("处理建议", causes_start)
            
            if next_section != -1:
                causes_section = analysis_text[causes_start:next_section].strip()
            else:
                causes_section = analysis_text[causes_start:].strip()
        
        if "处理建议" in analysis_text:
            suggestions_start = analysis_text.find("处理建议")
            suggestions_section = analysis_text[suggestions_start:].strip()
        
        # 创建分析结果
        AlertAnalysis.objects.create(
            alert=alert,
            analysis_text=analysis_text,
            priority_score=priority_score,
            potential_causes=causes_section,
            handling_suggestions=suggestions_section
        )
        
        logger.info(f"Created alert analysis for alert {alert_id}")
        return True
        
    except Alert.DoesNotExist:
        logger.error(f"Alert with id {alert_id} not found")
        return False
    except Exception as e:
        logger.error(f"Error analyzing alert: {str(e)}")
        return False

@shared_task
def generate_area_usage_pattern(area_id):
    """生成区域使用模式分析"""
    try:
        area = Area.objects.get(pk=area_id)
        
        # 获取最近30天的历史数据
        end_time = datetime.now()
        start_time = end_time - timedelta(days=30)
        
        # 获取人流量数据
        historical_data = HistoricalData.objects.filter(
            area=area,
            timestamp__gte=start_time,
            timestamp__lte=end_time
        ).order_by('timestamp')
        
        if not historical_data:
            logger.warning(f"No historical data for area {area.name} to analyze usage pattern")
            return False
        
        # 转换为DataFrame处理
        data = pd.DataFrame(list(historical_data.values('detected_count', 'timestamp')))
        data.columns = ['crowd', 'timestamp']
        
        # 提取时间特征
        data['hour'] = data['timestamp'].dt.hour
        data['day_of_week'] = data['timestamp'].dt.dayofweek
        data['date'] = data['timestamp'].dt.date
        
        # 计算日内模式 (每小时平均人流量)
        daily_pattern = data.groupby('hour')['crowd'].mean().to_dict()
        
        # 计算周内模式 (每天平均人流量)
        weekly_pattern = data.groupby('day_of_week')['crowd'].mean().to_dict()
        
        # 计算高峰时段 (人流量最高的3个小时)
        peak_hours = sorted(daily_pattern.items(), key=lambda x: x[1], reverse=True)[:3]
        peak_hours = [{"hour": hour, "average_crowd": crowd} for hour, crowd in peak_hours]
        
        # 计算低谷时段 (人流量最低的3个小时)
        quiet_hours = sorted(daily_pattern.items(), key=lambda x: x[1])[:3]
        quiet_hours = [{"hour": hour, "average_crowd": crowd} for hour, crowd in quiet_hours]
        
        # 创建或更新区域使用模式
        pattern, created = AreaUsagePattern.objects.update_or_create(
            area=area,
            defaults={
                'daily_pattern': daily_pattern,
                'weekly_pattern': weekly_pattern,
                'peak_hours': peak_hours,
                'quiet_hours': quiet_hours,
                'average_duration': 45.0,  # 假设平均停留时间，实际应该基于更复杂的分析
                'typical_user_groups': "学生、教职工"  # 假设用户群体，实际应该基于更复杂的分析
            }
        )
        
        logger.info(f"{'Created' if created else 'Updated'} usage pattern for area: {area.name}")
        return True
        
    except Area.DoesNotExist:
        logger.error(f"Area with id {area_id} not found")
        return False
    except Exception as e:
        logger.error(f"Error generating area usage pattern: {str(e)}")
        return False

@shared_task
def generate_personalized_recommendations():
    """为所有活跃用户生成个性化推荐"""
    try:
        # 获取最近7天活跃的用户 (假设通过登录记录或其他活动判断)
        active_users = CustomUser.objects.all()[:100]  # 简化处理，获取前100个用户
        
        recommendations_created = 0
        
        for user in active_users:
            # 获取用户的收藏区域
            favorite_areas = user.favorite_areas.all()
            favorite_building_ids = set(favorite_areas.values_list('type', flat=True))
            
            # 如果用户有收藏区域，推荐同类型的其他区域
            recommended_areas = []
            
            if favorite_areas.exists():
                # 找出同建筑类型但用户未收藏的区域
                similar_areas = Area.objects.filter(
                    type__id__in=favorite_building_ids
                ).exclude(
                    id__in=favorite_areas.values_list('id', flat=True)
                ).order_by('?')[:3]  # 随机选择3个
                
                recommended_areas.extend(list(similar_areas))
            
            # 如果推荐数量不足3个，补充一些人流量适中的区域
            if len(recommended_areas) < 3:
                try:
                    # 获取所有区域的检测到的人数
                    areas_with_data = []
                    for area in Area.objects.exclude(id__in=[a.id for a in recommended_areas + list(favorite_areas)]):
                        node = area.bound_node
                        if node and node.detected_count is not None:
                            areas_with_data.append({
                                "area": area,
                                "crowd": node.detected_count
                            })
                    
                    # 选择人流量适中的区域
                    if areas_with_data:
                        # 排序并选择中间的几个区域
                        sorted_areas = sorted(areas_with_data, key=lambda x: x["crowd"])
                        middle_start = max(0, len(sorted_areas)//2 - 1)
                        middle_areas = sorted_areas[middle_start:middle_start+(3-len(recommended_areas))]
                        recommended_areas.extend([item["area"] for item in middle_areas])
                
                except Exception as e:
                    logger.warning(f"Error getting crowd data for recommendations: {str(e)}")
            
            # 如果仍然不足3个，随机补充
            if len(recommended_areas) < 3:
                remaining = 3 - len(recommended_areas)
                random_areas = Area.objects.exclude(
                    id__in=[a.id for a in recommended_areas + list(favorite_areas)]
                ).order_by('?')[:remaining]
                
                recommended_areas.extend(list(random_areas))
            
            # 创建推荐记录
            for area in recommended_areas:
                # 生成推荐理由
                if area.type.id in favorite_building_ids:
                    reason = f"基于您对{area.type.name}的偏好推荐"
                    score = 0.85
                else:
                    reason = "这个区域当前人流量适中，环境舒适"
                    score = 0.75
                
                # 删除旧的推荐
                UserRecommendation.objects.filter(user=user, area=area).delete()
                
                # 保存推荐记录
                UserRecommendation.objects.create(
                    user=user,
                    area=area,
                    score=score,
                    reason=reason
                )
                
                recommendations_created += 1
        
        logger.info(f"Generated {recommendations_created} recommendations for {len(active_users)} users")
        return True
    
    except Exception as e:
        logger.error(f"Error generating personalized recommendations: {str(e)}")
        return False

@shared_task
def schedule_recurring_tasks():
    """调度定期任务"""
    # 为所有区域生成使用模式分析
    for area in Area.objects.all():
        if not AreaUsagePattern.objects.filter(area=area).exists() or \
           AreaUsagePattern.objects.get(area=area).last_updated < datetime.now() - timedelta(days=7):
            generate_area_usage_pattern.delay(area.id)
    
    # 为所有用户生成个性化推荐
    generate_personalized_recommendations.delay()
    
    # 分析所有未处理的告警
    for alert in Alert.objects.filter(solved=False):
        if not AlertAnalysis.objects.filter(alert=alert).exists():
            analyze_alert.delay(alert.id)
    
    return True