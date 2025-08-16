"""
会话记忆模块
- 提供基于缓存的轻量记忆
- 可选持久化到数据库（使用 GeneratedContent 作为简单备份示例）
"""
from __future__ import annotations

from typing import List, Dict, Optional
from django.core.cache import cache
from django.utils import timezone
import json
import logging

try:
    # 可选持久化支持
    from .models import GeneratedContent
except Exception:
    GeneratedContent = None  # 迁移未完成时避免导入错误

logger = logging.getLogger(__name__)

CACHE_PREFIX = "llm_chat_memory:"
DEFAULT_TTL_SEC = 60 * 60 * 6  # 6小时
MAX_HISTORY = 20


class ChatMemoryStore:
    """简单的聊天记忆存取封装"""

    @staticmethod
    def _key(session_id: str) -> str:
        return f"{CACHE_PREFIX}{session_id}"

    @classmethod
    def get_history(cls, session_id: str) -> List[Dict]:
        data = cache.get(cls._key(session_id))
        if not data:
            return []
        try:
            return json.loads(data)
        except Exception:
            return []

    @classmethod
    def append(cls, session_id: str, role: str, content: str, ttl: int = DEFAULT_TTL_SEC) -> List[Dict]:
        history = cls.get_history(session_id)
        history.append({"role": role, "content": content, "ts": timezone.now().isoformat()})
        # 裁剪长度
        if len(history) > MAX_HISTORY:
            history = history[-MAX_HISTORY:]
        cache.set(cls._key(session_id), json.dumps(history, ensure_ascii=False), ttl)
        return history

    @classmethod
    def set_history(cls, session_id: str, history: List[Dict], ttl: int = DEFAULT_TTL_SEC):
        # 只保留必要字段
        compact = [
            {"role": h.get("role"), "content": h.get("content"), "ts": h.get("ts")}
            for h in history[-MAX_HISTORY:]
            if h.get("role") in ("user", "assistant") and h.get("content")
        ]
        cache.set(cls._key(session_id), json.dumps(compact, ensure_ascii=False), ttl)

    @classmethod
    def clear(cls, session_id: str):
        cache.delete(cls._key(session_id))

    @classmethod
    def persist_snapshot(cls, session_id: str, tag: str = ""):
        """将最近的记忆快照持久化保存（可选）"""
        if not GeneratedContent:
            return
        try:
            history = cls.get_history(session_id)
            if not history:
                return
            content = json.dumps({"session_id": session_id, "history": history}, ensure_ascii=False)
            # 使用模型允许的字段与枚举
            GeneratedContent.objects.create(
                content_type="summary",
                title=f"Memory Snapshot {timezone.now().strftime('%Y-%m-%d %H:%M:%S')} {tag}",
                content=content,
                prompt_used="memory snapshot auto-persist"
            )
        except Exception as e:
            logger.warning(f"persist_snapshot failed: {e}")


def normalize_frontend_history(history: Optional[List[Dict]]) -> List[Dict]:
    """将前端历史标准化为 [ {role, content} ]"""
    if not history:
        return []
    out = []
    for item in history:
        role = item.get("role") or item.get("sender")
        content = item.get("content") or item.get("text")
        if role in ("user", "assistant") and content:
            out.append({"role": role, "content": content})
    return out[-MAX_HISTORY:]