import os
import json
import asyncio
from typing import List, Dict, Any, AsyncGenerator, Callable, Optional, Union
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from django.conf import settings
from django.utils import timezone
from django.db.models import Avg, Max, Min, Count, Q
from langchain.prompts import ChatPromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.callbacks import AsyncIteratorCallbackHandler
from langchain.schema import HumanMessage, SystemMessage, AIMessage

from webapi.models import Area, Building, HistoricalData, TemperatureHumidityData, Alert, Notice, CustomUser
from .models import LLMAnalysis, UserRecommendation, AlertAnalysis, AreaUsagePattern, GeneratedContent
from .tasks import analyze_area_data, analyze_alert, generate_area_usage_pattern

# 工具定义
class Tool:
    def __init__(self, name: str, description: str, func: Callable, parameters: Dict[str, Any] = None):
        self.name = name
        self.description = description
        self.func = func
        self.parameters = parameters or {}
    
    def __str__(self):
        params_str = ", ".join([f"{k}: {v}" for k, v in self.parameters.items()])
        return f"{self.name}({params_str}): {self.description}"

# 工具注册表
class ToolRegistry:
    def __init__(self):
        self.tools = {}
    
    def register(self, tool: Tool):
        self.tools[tool.name] = tool
        return self
    
    def get_tool(self, name: str) -> Optional[Tool]:
        return self.tools.get(name)
    
    def list_tools(self) -> List[Tool]:
        return list(self.tools.values())
    
    def get_tools_description(self) -> str:
        return "\n".join([str(tool) for tool in self.tools.values()])

# 创建工具注册表实例
tool_registry = ToolRegistry()

# 实现各种工具函数
async def get_area_list() -> List[Dict]:
    """获取所有区域列表"""
    areas = Area.objects.all().select_related('type', 'bound_node')
    return [{"id": area.id, "name": area.name, "building": area.type.name, "floor": area.floor} for area in areas]

async def get_area_details(area_id: int) -> Dict:
    """获取特定区域详情"""
    try:
        area = Area.objects.get(pk=area_id)
        node = area.bound_node
        return {
            "id": area.id,
            "name": area.name,
            "building": area.type.name,
            "floor": area.floor,
            "capacity": area.capacity,
            "description": area.description,
            "current_count": node.detected_count if node else None,
            "temperature": node.temperature if node else None,
            "humidity": node.humidity if node else None
        }
    except Area.DoesNotExist:
        return {"error": f"Area with id {area_id} not found"}

async def get_latest_environmental_data(area_id: int) -> Dict:
    """获取区域最新环境数据"""
    try:
        area = Area.objects.get(pk=area_id)
        node = area.bound_node
        
        # 从节点获取最新数据
        result = {
            "area_id": area.id,
            "area_name": area.name,
            "building": area.type.name,
            "floor": area.floor,
            "timestamp": timezone.now().isoformat()
        }
        
        if node:
            result.update({
                "crowd_count": node.detected_count,
                "temperature": node.temperature,
                "humidity": node.humidity,
                "last_updated": node.updated_at.isoformat() if node.updated_at else None
            })
        else:
            result.update({
                "message": "No sensor node bound to this area"
            })
            
        return result
    except Area.DoesNotExist:
        return {"error": f"Area with id {area_id} not found"}

async def get_crowd_stats() -> Dict:
    """获取所有区域人流量统计"""
    areas = Area.objects.all().select_related('bound_node', 'type')
    
    result = {
        "timestamp": datetime.now().isoformat(),
        "areas": []
    }
    
    for area in areas:
        node = area.bound_node
        area_data = {
            "id": area.id,
            "name": area.name,
            "building": area.type.name,
            "floor": area.floor,
            "capacity": area.capacity
        }
        
        if node:
            area_data["crowd_count"] = node.detected_count
            area_data["last_updated"] = node.updated_at.isoformat() if node.updated_at else None
        else:
            area_data["crowd_count"] = None
            area_data["last_updated"] = None
            
        result["areas"].append(area_data)
    
    # 添加统计信息
    populated_areas = [a for a in result["areas"] if a.get("crowd_count") is not None]
    if populated_areas:
        result["most_crowded"] = max(populated_areas, key=lambda x: x["crowd_count"])
        result["least_crowded"] = min(populated_areas, key=lambda x: x["crowd_count"])
        result["total_people"] = sum(a["crowd_count"] for a in populated_areas)
        result["average_crowd"] = result["total_people"] / len(populated_areas)
    
    return result

async def get_latest_analysis(area_id: int) -> Dict:
    """获取区域最新分析结果"""
    try:
        area = Area.objects.get(pk=area_id)
        analysis = LLMAnalysis.objects.filter(area=area).order_by('-timestamp').first()
        
        if not analysis:
            return {"message": f"No analysis found for area '{area.name}'"}
        
        return {
            "area_id": area.id,
            "area_name": area.name,
            "building": area.type.name,
            "timestamp": analysis.timestamp.isoformat(),
            "analysis_text": analysis.analysis_text,
            "analysis_data": json.loads(analysis.analysis_data) if analysis.analysis_data else {},
            "alert_status": analysis.alert_status,
            "alert_message": analysis.alert_message
        }
    except Area.DoesNotExist:
        return {"error": f"Area with id {area_id} not found"}

async def trigger_area_analysis(area_id: int) -> Dict:
    """触发区域分析任务"""
    try:
        area = Area.objects.get(pk=area_id)
        # 检查最近一小时是否已有分析
        recent_analysis = LLMAnalysis.objects.filter(
            area=area,
            timestamp__gte=datetime.now() - timedelta(hours=1)
        ).first()
        
        if recent_analysis:
            return {
                "message": f"Recent analysis already exists for area '{area.name}'",
                "analysis_id": recent_analysis.id,
                "timestamp": recent_analysis.timestamp.isoformat()
            }
        
        # 启动异步分析任务
        analyze_area_data.delay(area.id)
        return {
            "message": f"Analysis task started for area '{area.name}'",
            "area_id": area.id,
            "status": "processing"
        }
    except Area.DoesNotExist:
        return {"error": f"Area with id {area_id} not found"}

async def recommend_area(purpose: str = None) -> Dict:
    """基于目的推荐区域"""
    # 获取所有区域的人流量数据
    areas = Area.objects.all().select_related('bound_node', 'type')
    
    areas_with_data = []
    for area in areas:
        node = area.bound_node
        if node and node.detected_count is not None:
            areas_with_data.append({
                "id": area.id,
                "name": area.name,
                "building": area.type.name,
                "floor": area.floor,
                "capacity": area.capacity,
                "crowd_count": node.detected_count,
                "temperature": node.temperature,
                "humidity": node.humidity
            })
    
    if not areas_with_data:
        return {"message": "No areas with crowd data available for recommendation"}
    
    result = {
        "timestamp": datetime.now().isoformat(),
        "purpose": purpose,
        "recommendations": []
    }
    
    # 根据不同目的推荐区域
    if purpose and purpose.lower() in ["quiet", "study", "work", "安静", "学习", "工作"]:
        # 推荐人少的地方
        sorted_areas = sorted(areas_with_data, key=lambda x: x["crowd_count"])
        result["recommendations"] = sorted_areas[:3]
        result["recommendation_reason"] = "Selected least crowded areas for quiet activities"
    elif purpose and purpose.lower() in ["busy", "socialize", "event", "热闹", "社交", "活动"]:
        # 推荐人多的地方
        sorted_areas = sorted(areas_with_data, key=lambda x: x["crowd_count"], reverse=True)
        result["recommendations"] = sorted_areas[:3]
        result["recommendation_reason"] = "Selected most crowded areas for social activities"
    else:
        # 默认提供均衡推荐
        sorted_by_crowd = sorted(areas_with_data, key=lambda x: x["crowd_count"])
        result["recommendations"] = [
            sorted_by_crowd[0],  # 最少人
            sorted_by_crowd[len(sorted_by_crowd)//2],  # 中等人流
            sorted_by_crowd[-1]  # 最多人
        ]
        result["recommendation_reason"] = "Provided a balanced selection of areas with different crowd levels"
    
    return result

async def get_user_info(user_id: int) -> Dict:
    """获取用户信息，包括收藏区域等"""
    try:
        user = CustomUser.objects.get(pk=user_id)
        favorite_areas = user.favorite_areas.all().select_related('type')
        
        return {
            "id": user.id,
            "username": user.username,
            "role": user.role,
            "favorite_areas": [
                {"id": area.id, "name": area.name, "building": area.type.name}
                for area in favorite_areas
            ],
            "register_time": user.register_time.isoformat()
        }
    except CustomUser.DoesNotExist:
        return {"error": f"User with id {user_id} not found"}

async def get_personalized_recommendations(user_id: int, limit: int = 3) -> Dict:
    """为用户提供个性化区域推荐"""
    try:
        user = CustomUser.objects.get(pk=user_id)
        
        # 获取用户的推荐历史
        recommendations = UserRecommendation.objects.filter(
            user=user, 
            timestamp__gte=timezone.now() - timedelta(hours=24)
        ).order_by('-score')[:limit]
        
        # 如果有最近的推荐，直接返回
        if recommendations.exists():
            return {
                "user_id": user.id,
                "username": user.username,
                "recommendations": [
                    {
                        "area_id": rec.area.id,
                        "area_name": rec.area.name,
                        "building": rec.area.type.name,
                        "score": rec.score,
                        "reason": rec.reason
                    }
                    for rec in recommendations
                ],
                "timestamp": timezone.now().isoformat(),
                "source": "cached"
            }
        
        # 如果没有最近推荐，触发生成新推荐的任务
        from .tasks import generate_personalized_recommendations
        generate_personalized_recommendations.delay()
        
        # 返回临时推荐（基于收藏区域或人流量）
        favorite_areas = user.favorite_areas.all()
        if favorite_areas.exists():
            # 使用收藏区域的建筑类型作为推荐依据
            similar_areas = Area.objects.filter(
                type__in=favorite_areas.values_list('type', flat=True)
            ).exclude(
                id__in=favorite_areas.values_list('id', flat=True)
            ).order_by('?')[:limit]
            
            return {
                "user_id": user.id,
                "username": user.username,
                "recommendations": [
                    {
                        "area_id": area.id,
                        "area_name": area.name,
                        "building": area.type.name,
                        "score": 0.7,
                        "reason": f"与您收藏的{area.type.name}区域相似"
                    }
                    for area in similar_areas
                ],
                "timestamp": timezone.now().isoformat(),
                "source": "generated_temp"
            }
        else:
            # 推荐人流量适中的区域
            crowd_stats = await get_crowd_stats()
            if "areas" in crowd_stats and crowd_stats["areas"]:
                sorted_areas = sorted(crowd_stats["areas"], key=lambda x: x.get("crowd_count", 0) or 0)
                middle_start = max(0, len(sorted_areas)//2 - limit//2)
                recommendations = sorted_areas[middle_start:middle_start+limit]
                
                return {
                    "user_id": user.id,
                    "username": user.username,
                    "recommendations": [
                        {
                            "area_id": area["id"],
                            "area_name": area["name"],
                            "building": area["building"],
                            "score": 0.5,
                            "reason": "这个区域当前人流量适中，环境舒适"
                        }
                        for area in recommendations
                    ],
                    "timestamp": timezone.now().isoformat(),
                    "source": "generated_temp"
                }
            else:
                return {
                    "message": "正在为您生成个性化推荐，请稍后再试",
                    "status": "generating"
                }
    
    except CustomUser.DoesNotExist:
        return {"error": f"User with id {user_id} not found"}
    except Exception as e:
        return {"error": f"Error generating recommendations: {str(e)}"}

async def get_area_usage_pattern(area_id: int) -> Dict:
    """获取区域使用模式分析"""
    try:
        area = Area.objects.get(pk=area_id)
        
        # 尝试获取现有的使用模式分析
        try:
            pattern = AreaUsagePattern.objects.get(area=area)
            
            # 如果分析过期（超过7天），触发更新
            if pattern.last_updated < timezone.now() - timedelta(days=7):
                generate_area_usage_pattern.delay(area.id)
                update_status = "updating"
            else:
                update_status = "current"
                
            return {
                "area_id": area.id,
                "area_name": area.name,
                "daily_pattern": pattern.daily_pattern,
                "weekly_pattern": pattern.weekly_pattern,
                "peak_hours": pattern.peak_hours,
                "quiet_hours": pattern.quiet_hours,
                "average_duration": pattern.average_duration,
                "typical_user_groups": pattern.typical_user_groups,
                "last_updated": pattern.last_updated.isoformat(),
                "status": update_status
            }
            
        except AreaUsagePattern.DoesNotExist:
            # 如果没有分析，触发分析任务
            generate_area_usage_pattern.delay(area.id)
            
            return {
                "area_id": area.id,
                "area_name": area.name,
                "message": "区域使用模式分析正在生成中，请稍后查询",
                "status": "generating"
            }
    
    except Area.DoesNotExist:
        return {"error": f"Area with id {area_id} not found"}

async def get_alerts_summary() -> Dict:
    """获取告警摘要和分析"""
    # 获取未解决的告警
    active_alerts = Alert.objects.filter(solved=False).order_by('-grade', '-timestamp')
    
    if not active_alerts:
        return {
            "message": "当前没有活跃的告警",
            "active_alerts_count": 0,
            "timestamp": timezone.now().isoformat()
        }
    
    # 获取告警分析
    alerts_with_analysis = []
    
    for alert in active_alerts:
        alert_data = {
            "id": alert.id,
            "area_name": alert.area.name,
            "alert_type": alert.alert_type,
            "grade": alert.grade,
            "message": alert.message,
            "timestamp": alert.timestamp.isoformat(),
        }
        
        # 获取AI分析（如果有）
        try:
            analysis = AlertAnalysis.objects.get(alert=alert)
            alert_data["ai_analysis"] = {
                "priority_score": analysis.priority_score,
                "potential_causes": analysis.potential_causes,
                "handling_suggestions": analysis.handling_suggestions
            }
        except AlertAnalysis.DoesNotExist:
            # 如果没有分析，触发分析任务
            analyze_alert.delay(alert.id)
            alert_data["ai_analysis"] = {"status": "analyzing"}
        
        alerts_with_analysis.append(alert_data)
    
    # 按严重程度分组
    alerts_by_grade = {}
    for grade in range(4):  # 0-3级告警
        alerts_by_grade[grade] = [a for a in alerts_with_analysis if a.get("grade") == grade]
    
    return {
        "active_alerts_count": len(active_alerts),
        "alerts_by_grade": alerts_by_grade,
        "most_affected_areas": list(active_alerts.values('area__name').annotate(
            count=Count('id')).order_by('-count')[:5]),
        "most_common_types": list(active_alerts.values('alert_type').annotate(
            count=Count('id')).order_by('-count')[:3]),
        "timestamp": timezone.now().isoformat()
    }

async def generate_notice_for_area(area_id: int, notice_type: str = "status") -> Dict:
    """为区域生成智能公告"""
    try:
        area = Area.objects.get(pk=area_id)
        
        # 查看是否已有最近生成的公告
        recent_content = GeneratedContent.objects.filter(
            content_type='notice',
            related_area=area,
            generated_at__gte=timezone.now() - timedelta(hours=6)
        ).first()
        
        if recent_content:
            return {
                "area_id": area.id,
                "area_name": area.name,
                "notice": {
                    "id": recent_content.id,
                    "title": recent_content.title,
                    "content": recent_content.content,
                    "generated_at": recent_content.generated_at.isoformat(),
                    "published": recent_content.published
                },
                "status": "existing"
            }
        
        # 获取区域的实时数据
        node = area.bound_node
        current_data = {
            "crowd_count": node.detected_count if node else None,
            "temperature": node.temperature if node else None,
            "humidity": node.humidity if node else None
        }
        
        # 基于当前数据和通知类型生成公告
        if notice_type == "status":
            crowd_desc = "人流量适中" if current_data["crowd_count"] and current_data["crowd_count"] < 50 else "当前较为拥挤" if current_data["crowd_count"] else "人流量数据暂无"
            temp_desc = f"温度{current_data['temperature']}℃" if current_data["temperature"] else "温度适宜"
            
            title = f"{area.name}状态通知"
            content = f"尊敬的用户，{area.name}目前状态良好，环境舒适。{crowd_desc}，{temp_desc}。欢迎前来使用！"
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
        
        return {
            "area_id": area.id,
            "area_name": area.name,
            "notice": {
                "id": generated_content.id,
                "title": generated_content.title,
                "content": generated_content.content,
                "generated_at": generated_content.generated_at.isoformat(),
                "published": generated_content.published
            },
            "status": "generated"
        }
    
    except Area.DoesNotExist:
        return {"error": f"Area with id {area_id} not found"}

# 注册工具
tool_registry.register(Tool("get_area_list", "获取所有区域列表", get_area_list))
tool_registry.register(Tool("get_area_details", "获取特定区域的详细信息", get_area_details, {"area_id": "区域ID"}))
tool_registry.register(Tool("get_latest_environmental_data", "获取区域最新环境数据", get_latest_environmental_data, {"area_id": "区域ID"}))
tool_registry.register(Tool("get_crowd_stats", "获取所有区域人流量统计", get_crowd_stats))
tool_registry.register(Tool("get_latest_analysis", "获取区域最新分析结果", get_latest_analysis, {"area_id": "区域ID"}))
tool_registry.register(Tool("trigger_area_analysis", "触发区域分析任务", trigger_area_analysis, {"area_id": "区域ID"}))
tool_registry.register(Tool("recommend_area", "基于目的推荐区域", recommend_area, {"purpose": "目的(可选:安静/热闹)"}))
tool_registry.register(Tool("get_user_info", "获取用户信息", get_user_info, {"user_id": "用户ID"}))
tool_registry.register(Tool("get_personalized_recommendations", "获取个性化区域推荐", get_personalized_recommendations, 
                           {"user_id": "用户ID", "limit": "推荐数量(可选)"}))
tool_registry.register(Tool("get_area_usage_pattern", "获取区域使用模式分析", get_area_usage_pattern, {"area_id": "区域ID"}))
tool_registry.register(Tool("get_alerts_summary", "获取告警摘要和分析", get_alerts_summary))
tool_registry.register(Tool("generate_notice_for_area", "为区域生成智能公告", generate_notice_for_area, 
                           {"area_id": "区域ID", "notice_type": "公告类型(status/alert/maintenance)"}))

# 更新系统提示，包含新工具
SYSTEM_PROMPT = """你是一个校园设施智能助手，可以回答用户关于校园区域、人流量和环境数据的问题。
你可以使用以下工具来获取信息：

{tools_description}

当用户询问特定信息时，先分析用户意图，然后选择合适的工具获取数据，最后用自然语言回答用户问题。
如果需要区域ID但用户只提供了区域名称，请先调用get_area_list查找对应的ID。
保持回答简洁、专业且有帮助。不要编造数据，只使用工具返回的实际数据。

分析用户问题时，注意以下几类常见意图：
1. 查询类：询问特定区域或传感器数据的当前状态
2. 比较类：询问不同区域之间的对比或排名(最多人/最少人/最热/最冷等)
3. 推荐类：请求推荐去哪个区域(学习/社交/活动等)
4. 分析类：询问特定区域的数据分析结果或趋势
5. 个性化类：基于用户喜好的个性化推荐或信息
6. 告警类：关于系统告警的查询或处理建议
7. 公告类：生成或查询区域公告

为用户提供有价值的信息和建议，帮助他们做出更好的决策。
"""

async def analyze_intent(user_message: str) -> List[Dict]:
    """分析用户意图并确定需要调用的工具"""
    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=SYSTEM_PROMPT.format(
            tools_description=tool_registry.get_tools_description()
        )),
        HumanMessage(content=f"用户问题: {user_message}\n\n请分析这个问题需要调用哪些工具，按顺序列出工具名称和参数，格式为JSON数组。")
    ])
    
    callback = AsyncIteratorCallbackHandler()
    llm = ChatOpenAI(
        temperature=0,
        streaming=True,
        callbacks=[callback],
        openai_api_key=settings.OPENAI_API_KEY
    )
    
    task = asyncio.create_task(llm.agenerate([prompt.to_messages()]))
    result = ""
    async for chunk in callback.aiter():
        result += chunk
    
    await task
    
    # 尝试从结果中提取JSON工具调用列表
    try:
        # 查找JSON数组开始和结束的位置
        start_idx = result.find('[')
        end_idx = result.rfind(']') + 1
        
        if start_idx >= 0 and end_idx > start_idx:
            json_str = result[start_idx:end_idx]
            tools_to_call = json.loads(json_str)
            return tools_to_call
        else:
            # 回退策略：基于关键词判断工具
            tools_to_call = []
            
            # 简单的关键词匹配
            if any(word in user_message.lower() for word in ["列表", "所有", "有哪些", "区域"]):
                tools_to_call.append({"name": "get_area_list", "parameters": {}})
            
            if any(word in user_message.lower() for word in ["人流", "拥挤", "人多", "人少", "最多", "最少"]):
                tools_to_call.append({"name": "get_crowd_stats", "parameters": {}})
            
            if any(word in user_message.lower() for word in ["推荐", "建议", "哪里好", "去哪"]):
                purpose = "安静" if any(word in user_message.lower() for word in ["安静", "学习", "工作"]) else "热闹"
                tools_to_call.append({"name": "recommend_area", "parameters": {"purpose": purpose}})
            
            return tools_to_call
    except Exception as e:
        # 如果JSON解析失败，使用默认工具
        return [{"name": "get_crowd_stats", "parameters": {}}]

async def execute_tools(tools_to_call: List[Dict]) -> List[Dict]:
    """执行工具调用并返回结果"""
    results = []
    
    for tool_call in tools_to_call:
        tool_name = tool_call.get("name")
        parameters = tool_call.get("parameters", {})
        
        tool = tool_registry.get_tool(tool_name)
        if tool:
            try:
                result = await tool.func(**parameters)
                results.append({
                    "tool": tool_name,
                    "parameters": parameters,
                    "result": result
                })
            except Exception as e:
                results.append({
                    "tool": tool_name,
                    "parameters": parameters,
                    "error": str(e)
                })
        else:
            results.append({
                "tool": tool_name,
                "parameters": parameters,
                "error": f"Tool '{tool_name}' not found"
            })
    
    return results

async def generate_response(user_message: str, tools_results: List[Dict], chat_history: List[Dict]) -> str:
    """生成对用户消息的自然语言响应"""
    # 构建对话历史
    messages = []
    
    # 添加系统提示
    messages.append(SystemMessage(content=SYSTEM_PROMPT.format(
        tools_description=tool_registry.get_tools_description()
    )))
    
    # 添加聊天历史
    for msg in chat_history:
        if msg.get("role") == "user":
            messages.append(HumanMessage(content=msg.get("content", "")))
        elif msg.get("role") == "assistant":
            messages.append(AIMessage(content=msg.get("content", "")))
    
    # 添加当前用户消息和工具结果
    tools_results_str = json.dumps(tools_results, ensure_ascii=False, indent=2)
    messages.append(HumanMessage(content=f"用户问题: {user_message}\n\n工具调用结果:\n{tools_results_str}"))
    
    # 生成响应
    callback = AsyncIteratorCallbackHandler()
    llm = ChatOpenAI(
        temperature=0.7,
        streaming=True,
        callbacks=[callback],
        openai_api_key=settings.OPENAI_API_KEY
    )
    
    task = asyncio.create_task(llm.agenerate([messages]))
    
    async for chunk in callback.aiter():
        yield chunk
    
    await task

async def get_agent_response(user_message: str, chat_history: List[Dict] = None) -> AsyncGenerator[str, None]:
    """处理用户消息并生成代理响应"""
    if chat_history is None:
        chat_history = []
    
    try:
        # 1. 分析用户意图，确定要调用的工具
        tools_to_call = await analyze_intent(user_message)
        
        # 2. 执行工具调用
        tools_results = await execute_tools(tools_to_call)
        
        # 3. 生成自然语言响应
        async for chunk in generate_response(user_message, tools_results, chat_history):
            yield chunk
    except Exception as e:
        yield f"很抱歉，处理您的请求时出现了错误: {str(e)}"