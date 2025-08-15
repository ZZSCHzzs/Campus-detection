"""
LLM 公共工具模块
提供统一的LLM客户端和流式响应接口，支持多模型配置
"""
import os
import logging
import asyncio
from typing import Optional, List, AsyncGenerator

# 强制使用pydantic v1的验证器重用，避免langchain相关问题
import pydantic.v1.config
pydantic.v1.config.PYDANTIC_VALIDATOR_REUSE = True

# LangChain imports
from langchain_openai import ChatOpenAI
from langchain.callbacks import AsyncIteratorCallbackHandler
from langchain.schema import HumanMessage, SystemMessage, AIMessage, BaseMessage

logger = logging.getLogger('django.llm')

# 模型配置映射 - SiliconFlow API 配置
MODEL_CONFIGS = {
    # 推理模型 - 用于复杂分析和工具调用（使用快速推理模型）
    "reasoning": {
        "model": os.getenv("LLM_REASONING_MODEL", "Qwen/Qwen3-30B-A3B-Thinking-2507"),
        "api_key": os.getenv("LLM_REASONING_API_KEY", os.getenv("SILICONFLOW_API_KEY", "")),
        "api_base": os.getenv("LLM_REASONING_API_BASE", "https://api.siliconflow.cn/v1"),
        "max_tokens": int(os.getenv("LLM_REASONING_MAX_TOKENS", "8192")),
        "description": "快速推理模型，带有<think></think>思考过程，用于复杂分析和工具调用"
    },
    
    # 快速模型 - 用于闲聊和简单回答
    "fast": {
        "model": os.getenv("LLM_FAST_MODEL", "Qwen/Qwen3-30B-A3B-Instruct-2507"),
        "api_key": os.getenv("LLM_FAST_API_KEY", os.getenv("SILICONFLOW_API_KEY", "")),
        "api_base": os.getenv("LLM_FAST_API_BASE", "https://api.siliconflow.cn/v1"),
        "max_tokens": int(os.getenv("LLM_FAST_MAX_TOKENS", "8192")),
        "description": "快速模型，用于日常对话和简单回答"
    },
    
    # 分析模型 - 用于数据分析和报告生成（使用标准模型）
    "analysis": {
        "model": os.getenv("LLM_ANALYSIS_MODEL", "Qwen/Qwen3-235B-A22B-Instruct-2507"),
        "api_key": os.getenv("LLM_ANALYSIS_API_KEY", os.getenv("SILICONFLOW_API_KEY", "")),
        "api_base": os.getenv("LLM_ANALYSIS_API_BASE", "https://api.siliconflow.cn/v1"),
        "max_tokens": int(os.getenv("LLM_ANALYSIS_MAX_TOKENS", "8192")),
        "description": "标准大模型，专门用于数据分析和结构化输出"
    },
    
    # 深度推理模型 - 用于复杂长文本分析（可选，用于特殊场景）
    "deep_reasoning": {
        "model": os.getenv("LLM_DEEP_MODEL", "Tongyi-Zhiwen/QwenLong-L1-32B"),
        "api_key": os.getenv("LLM_DEEP_API_KEY", os.getenv("SILICONFLOW_API_KEY", "")),
        "api_base": os.getenv("LLM_DEEP_API_BASE", "https://api.siliconflow.cn/v1"),
        "max_tokens": int(os.getenv("LLM_DEEP_MAX_TOKENS", "32768")),
        "description": "深度推理模型，用于复杂长文本分析和深度思考"
    },
    
    # 默认模型 - 兜底配置（使用快速模型）
    "default": {
        "model": os.getenv("LLM_MODEL", "Qwen/Qwen3-30B-A3B-Instruct-2507"),
        "api_key": os.getenv("LLM_API_KEY", os.getenv("SILICONFLOW_API_KEY", "")),
        "api_base": os.getenv("LLM_API_BASE", "https://api.siliconflow.cn/v1"),
        "max_tokens": int(os.getenv("LLM_MAX_TOKENS", "8192")),
        "description": "默认兜底模型"
    }
}


def get_llm_client(
    temperature: float = 0.7,
    streaming: bool = False,
    callbacks: Optional[List] = None,
    model_type: str = "default"
) -> ChatOpenAI:
    """
    获取统一的LLM客户端实例，支持多模型配置
    
    Args:
        temperature: 生成温度，越高越随机
        streaming: 是否使用流式输出
        callbacks: 回调处理器列表
        model_type: 模型类型 ["reasoning", "fast", "analysis", "deep_reasoning", "default"]
    
    Returns:
        配置好的ChatOpenAI实例
    """
    # 获取模型配置
    config = MODEL_CONFIGS.get(model_type, MODEL_CONFIGS["default"])
    
    # 如果指定模型配置为空，回退到默认配置
    if not config["model"] or not config["api_key"]:
        logger.warning(f"Model type '{model_type}' not configured, falling back to default")
        config = MODEL_CONFIGS["default"]
    
    llm = ChatOpenAI(
        temperature=temperature,
        streaming=streaming,
        callbacks=callbacks,
        model=config["model"],
        openai_api_key=config["api_key"],
        openai_api_base=config["api_base"],
        max_tokens=config["max_tokens"]
    )
    return llm


async def stream_chat_response(
    messages: List[BaseMessage],
    temperature: float = 0.7,
    model_type: str = "fast"
) -> AsyncGenerator[str, None]:
    """
    流式生成LLM回答
    
    Args:
        messages: 消息列表
        temperature: 生成温度
        model_type: 使用的模型类型，默认使用快速模型
    """
    try:
        callback = AsyncIteratorCallbackHandler()
        llm = get_llm_client(
            temperature=temperature, 
            streaming=True, 
            callbacks=[callback],
            model_type=model_type
        )
        task = asyncio.create_task(llm.agenerate([messages]))

        # 仅在推理类模型时，过滤<think>内容
        filter_think = model_type in ("reasoning", "deep_reasoning")
        inside_think = False
        buffer = ""

        async for chunk in callback.aiter():
            text = str(chunk)
            if filter_think:
                buffer += text
                out = []
                i = 0
                while i < len(buffer):
                    if not inside_think and buffer.startswith("<think>", i):
                        inside_think = True
                        i += len("<think>")
                        continue
                    if inside_think:
                        end_idx = buffer.find("</think>", i)
                        if end_idx == -1:
                            # 尚未读到结束标签，整段丢弃，等待更多chunk
                            i = len(buffer)
                            buffer = buffer  # 保留以便下次继续匹配
                            break
                        else:
                            # 跳过结束标签
                            inside_think = False
                            i = end_idx + len("</think>")
                            continue
                    # 正常输出字符
                    out.append(buffer[i])
                    i += 1
                # 如果所有内容都被消费且不在think中，清空缓冲
                if not inside_think:
                    buffer = buffer[i:]
                yield "".join(out)
            else:
                yield text
        await task
    except Exception as e:
        logger.error(f"流式生成回答出错: {str(e)}", exc_info=True)
        yield f"生成回答时出现错误: {str(e)}"


async def run_llm_with_retry(
    messages: List[BaseMessage],
    max_retries: int = 3,
    temperature: float = 0.7,
    model_type: str = "default"
) -> str:
    """
    运行LLM推理，带有重试机制
    
    Args:
        messages: 消息列表
        max_retries: 最大重试次数
        temperature: 生成温度
        model_type: 使用的模型类型
    """
    llm = get_llm_client(
        temperature=temperature,
        model_type=model_type
    )
    retries = 0
    while retries < max_retries:
        try:
            response = await llm.agenerate([messages])
            text = response.generations[0][0].text
            # 推理类模型会返回<think>...</think>，对终端用户隐藏
            if model_type in ("reasoning", "deep_reasoning"):
                try:
                    import re
                    text = re.sub(r"<think>[\s\S]*?</think>", "", text, flags=re.IGNORECASE)
                except Exception:
                    pass
            return text.strip()
        except Exception as e:
            retries += 1
            if retries >= max_retries:
                logger.error(f"LLM推理失败，已达到最大重试次数: {str(e)}", exc_info=True)
                raise
            logger.warning(f"LLM推理失败，正在重试({retries}/{max_retries}): {str(e)}")
            await asyncio.sleep(1)  # 重试前等待1秒


def get_model_info() -> dict:
    """获取当前模型配置信息，用于调试和监控"""
    return {
        "available_types": list(MODEL_CONFIGS.keys()),
        "configs": {
            k: {
                "model": v["model"] or "未配置",
                "api_base": v["api_base"] or "未配置", 
                "max_tokens": v["max_tokens"],
                "description": v["description"],
                "configured": bool(v["model"] and v["api_key"])
            }
            for k, v in MODEL_CONFIGS.items()
        }
    }