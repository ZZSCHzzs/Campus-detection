from django.apps import AppConfig


class WebapiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'webapi'

    def ready(self):
       
        # 检查并记录channels配置
        from django.conf import settings
        import logging
        
        logger = logging.getLogger('terminal_ws')
        
        if hasattr(settings, 'CHANNEL_LAYERS'):
            backend = settings.CHANNEL_LAYERS.get('default', {}).get('BACKEND', 'Not configured')
            logger.info(f"Channels layer backend: {backend}")
            
            # 测试Redis连接
            if 'redis' in backend.lower():
                try:
                    from channels.layers import get_channel_layer
                    channel_layer = get_channel_layer()
                    logger.info("Redis channel layer initialized successfully")
                except Exception as e:
                    logger.error(f"Redis channel layer initialization error: {str(e)}")
        else:
            logger.warning("CHANNEL_LAYERS not configured in settings")
