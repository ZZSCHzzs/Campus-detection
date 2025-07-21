import logging
from datetime import timedelta
from django.utils import timezone
from django.core.cache import cache
from .models import ProcessTerminal

logger = logging.getLogger('django')

def check_terminal_connections():
    """
    定期检查所有终端的连接状态，
    如果终端长时间未活动，则标记为离线
    """
    try:
        # 设置超时时间（3分钟）
        timeout = timezone.now() - timedelta(minutes=3)
        
        # 查找所有标记为在线但长时间未活动的终端
        inactive_terminals = ProcessTerminal.objects.filter(
            status=True,  # 当前标记为在线
            last_active__lt=timeout  # 但最后活动时间超过3分钟
        )
        
        # 更新这些终端的状态为离线
        count = 0
        for terminal in inactive_terminals:
            # 检查缓存中是否有连接状态
            cache_key = f"terminal:{terminal.id}:connected"
            is_connected = cache.get(cache_key)
            
            # 如果缓存明确指示为未连接，或者缓存中没有该值（判断为未连接）
            if is_connected is False or is_connected is None:
                terminal.status = False
                terminal.save(update_fields=['status'])
                
                # 更新状态缓存
                status_cache_key = f"terminal:{terminal.id}:status"
                cached_status = cache.get(status_cache_key)
                if cached_status:
                    cached_status.update({"terminal_online": False})
                    cache.set(status_cache_key, cached_status, timeout=60)
                
                count += 1
                logger.info(f"终端 {terminal.id} 已自动标记为离线 (长时间未活动)")
        
        if count > 0:
            logger.info(f"共有 {count} 个终端被自动标记为离线")
        
        return count
    except Exception as e:
        logger.error(f"检查终端连接状态时出错: {str(e)}")
        return 0
