import time
import threading
from enum import Enum
from gpiozero import Buzzer, Device
try:
    # 尝试优先使用 lgpio 引脚工厂，避免旧版 RPi.GPIO 的基址报错
    from gpiozero.pins.lgpio import LGPIOFactory
    Device.pin_factory = LGPIOFactory()
except Exception:
    # 未安装 lgpio 时，gpiozero 会回退到其它可用 pin factory
    pass

class BuzzerPattern(Enum):
    """蜂鸣器模式枚举"""
    SINGLE_BEEP = 1      # 单次短鸣
    DOUBLE_BEEP = 2      # 双短鸣
    LONG_BEEP = 3        # 长鸣
    SOS = 4              # SOS紧急信号
    ALARM = 5            # 警报信号
    CUSTOM = 6           # 自定义模式

class BuzzerManager:
    """蜂鸣器管理类，用于控制连接到树莓派的蜂鸣器"""
    
    def __init__(self, pin_trigger=2, pin_echo=9, pin_buzzer=11, log_manager=None):
        """
        初始化蜂鸣器管理器
        
        Args:
            pin_trigger: 触发引脚号
            pin_echo: 回声引脚号
            pin_buzzer: 蜂鸣器引脚号
            log_manager: 日志管理器实例
        """
        self.pin_trigger = pin_trigger
        self.pin_echo = pin_echo
        self.pin_buzzer = pin_buzzer
        self.log_manager = log_manager
        self._buzzing = False
        self._stop_event = threading.Event()
        self._buzzer_thread = None

        # 使用 gpiozero 初始化蜂鸣器
        try:
            self._buzzer = Buzzer(self.pin_buzzer)  # 默认 BCM 编号
            if self.log_manager:
                self.log_manager.info(
                    f"蜂鸣器管理器初始化完成 - 引脚: 触发={pin_trigger}, 回声={pin_echo}, 蜂鸣器={pin_buzzer}"
                )
        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"初始化蜂鸣器管理器失败: {str(e)}")
            else:
                print(f"初始化蜂鸣器管理器失败: {str(e)}")
            raise

    def cleanup(self):
        """清理资源"""
        self.stop_buzzer()
        time.sleep(0.1)
        try:
            if hasattr(self, "_buzzer"):
                self._buzzer.close()
            if self.log_manager:
                self.log_manager.info("蜂鸣器资源已清理")
        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"清理蜂鸣器资源失败: {str(e)}")

    def beep(self, duration=0.5):
        """使蜂鸣器鸣叫指定时长"""
        try:
            self._buzzer.on()
            time.sleep(duration)
            self._buzzer.off()
        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"蜂鸣器鸣叫失败: {str(e)}")

    def start_buzzer(self, pattern=BuzzerPattern.SINGLE_BEEP, repeat=1, custom_pattern=None):
        """
        开始蜂鸣器鸣叫，使用指定模式
        
        Args:
            pattern: 鸣叫模式
            repeat: 重复次数
            custom_pattern: 自定义模式列表，每项为(开启时长, 关闭时长)
        """
        # 如果已经在鸣叫，先停止
        if self._buzzing:
            self.stop_buzzer()
            time.sleep(0.1)  # 短暂等待确保之前的线程停止
        
        # 重置停止事件
        self._stop_event.clear()
        self._buzzing = True
        
        # 创建并启动蜂鸣器线程
        self._buzzer_thread = threading.Thread(
            target=self._buzzer_worker,
            args=(pattern, repeat, custom_pattern)
        )
        self._buzzer_thread.daemon = True
        self._buzzer_thread.start()
        
        if self.log_manager:
            self.log_manager.info(f"蜂鸣器已启动 - 模式: {pattern.name}, 重复次数: {repeat}")
    
    def stop_buzzer(self):
        """停止蜂鸣器鸣叫"""
        if self._buzzing:
            self._stop_event.set()
            self._buzzing = False
            try:
                self._buzzer.off()
            except Exception as e:
                if self.log_manager:
                    self.log_manager.error(f"关闭蜂鸣器失败: {str(e)}")
            if self.log_manager:
                self.log_manager.info("蜂鸣器已停止")

    def _buzzer_worker(self, pattern, repeat, custom_pattern=None):
        """
        蜂鸣器工作线程
        
        Args:
            pattern: 鸣叫模式
            repeat: 重复次数
            custom_pattern: 自定义模式列表，每项为(开启时长, 关闭时长)
        """
        try:
            count = 0
            while count < repeat and not self._stop_event.is_set():
                if pattern == BuzzerPattern.SINGLE_BEEP:
                    self._play_pattern([(0.2, 0.1)])
                
                elif pattern == BuzzerPattern.DOUBLE_BEEP:
                    self._play_pattern([(0.15, 0.1), (0.15, 0.5)])
                
                elif pattern == BuzzerPattern.LONG_BEEP:
                    self._play_pattern([(1.0, 0.5)])
                
                elif pattern == BuzzerPattern.SOS:
                    # SOS摩尔斯电码: ... --- ...
                    self._play_pattern([
                        (0.2, 0.2), (0.2, 0.2), (0.2, 0.2),  # S (3短)
                        (0.6, 0.2), (0.6, 0.2), (0.6, 0.2),  # O (3长)
                        (0.2, 0.2), (0.2, 0.2), (0.2, 0.2),  # S (3短)
                    ])
                
                elif pattern == BuzzerPattern.ALARM:
                    # 警报模式: 快速间歇鸣叫
                    self._play_pattern([(0.2, 0.2)] * 5)
                
                elif pattern == BuzzerPattern.CUSTOM and custom_pattern:
                    self._play_pattern(custom_pattern)
                
                count += 1
                
                # 在每次重复之间添加一个短暂的停顿
                if count < repeat and not self._stop_event.is_set():
                    time.sleep(0.5)
                    
        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"蜂鸣器工作线程异常: {str(e)}")
        finally:
            try:
                self._buzzer.off()
                self._buzzing = False
            except Exception as e:
                if self.log_manager:
                    self.log_manager.error(f"关闭蜂鸣器失败: {str(e)}")

    def _play_pattern(self, pattern):
        """
        播放蜂鸣模式
        
        Args:
            pattern: 模式列表，每项为(开启时长, 关闭时长)
        """
        for on_time, off_time in pattern:
            if self._stop_event.is_set():
                break
            try:
                self._buzzer.on()
                time.sleep(on_time)
            except Exception as e:
                if self.log_manager:
                    self.log_manager.error(f"开启蜂鸣器失败: {str(e)}")
            try:
                self._buzzer.off()
                time.sleep(off_time)
            except Exception as e:
                if self.log_manager:
                    self.log_manager.error(f"关闭蜂鸣器失败: {str(e)}")

    def is_active(self):
        """返回蜂鸣器是否处于激活状态"""
        return self._buzzing