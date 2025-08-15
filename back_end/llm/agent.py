import logging
from typing import List, Dict, AsyncGenerator, Optional
import asyncio

from langchain.schema import HumanMessage, SystemMessage, AIMessage, BaseMessage
import json

from .utils import stream_chat_response
from .chains import stream_route_and_respond

logger = logging.getLogger('django.llm.agent')


def _normalize_history(history: Optional[List[Dict]]) -> List[BaseMessage]:
    """
    将前端传入的聊天历史规范化为LangChain的消息对象列表。
    允许的输入格式示例：
    [
        {"role": "system", "content": "你是校园智能助手"},
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": "你好，请问有什么可以帮你？"}
    ]
    """
    messages: List[BaseMessage] = []
    if not history:
        return messages

    for item in history:
        if not isinstance(item, dict):
            continue
        role = (item.get("role") or "").lower()
        content = item.get("content")
        if not content:
            continue
        if role == "system":
            messages.append(SystemMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))
        else:
            messages.append(HumanMessage(content=content))
    return messages


async def get_agent_response(
    user_message: str,
    history: Optional[List[Dict]] = None,
    system_prompt: Optional[str] = None,
    temperature: float = 0.7,
    model_type: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    """
    代理响应接口：
    - 若提供自定义 system_prompt，则走基础流式对话（与原实现兼容）。
    - 否则默认走路由链，自动识别意图并调用工具与提示词。
    可选的 model_type 用于指定生成所使用的模型类型。
    """
    try:
        if system_prompt:
            # 兼容模式：直接使用system_prompt + 历史 + 用户输入 进行流式对话
            msg_list: List[BaseMessage] = []
            msg_list.append(SystemMessage(content=system_prompt))
            msg_list.extend(_normalize_history(history))
            msg_list.append(HumanMessage(content=user_message))

            # 统一输出为逐行JSON事件，避免前端解析不一致
            yield json.dumps({
                "type": "chain_start",
                "step": "llm_streaming",
                "message": "💬 正在生成回答..."
            }, ensure_ascii=False) + "\n"
            await asyncio.sleep(0)

            async for chunk in stream_chat_response(msg_list, temperature=temperature, model_type=(model_type or "fast")):
                yield json.dumps({"type": "content", "text": chunk}, ensure_ascii=False) + "\n"
                await asyncio.sleep(0)

            yield json.dumps({"type": "chain_end", "message": "✅ 处理完成"}, ensure_ascii=False) + "\n"
            await asyncio.sleep(0)
            return

        # 默认：走带工具/提示词的路由链（含真正逐步流式输出）
        async for chunk in stream_route_and_respond(user_message, history or [], model_type=model_type):
            yield chunk
    except Exception as e:
        logger.error(f"生成代理响应失败: {str(e)}", exc_info=True)
        yield json.dumps({
            "type": "error",
            "message": f"❌ 生成响应失败: {str(e)}"
        }, ensure_ascii=False) + "\n"