#!/usr/bin/env python3
import time
import json
import os
import logging

logger = logging.getLogger('sgp30_reader')


class SGP30Reader:
    """
    SGP30传感器CO2读数模块

    功能：
    - 自动初始化传感器
    - 提供稳定的CO2读数
    - 自动管理基线校准
    - 异常自动恢复

    使用方法：
    from sgp30_reader import SGP30Reader

    reader = SGP30Reader()
    co2_ppm = reader.get_co2()  # 获取最新CO2读数
    """

    def __init__(self, i2c_bus=1, baseline_file="sgp30_baseline.json", log_manager=None):
        """
        初始化传感器
        :param i2c_bus: I2C总线编号 (树莓派通常为1)
        :param baseline_file: 基线校准文件路径
        :param log_manager: 统一日志管理器
        """
        self.bus_num = i2c_bus
        self.baseline_file = baseline_file
        self.bus = None
        self.sensor = None
        self._available = False
        self.log_manager = log_manager
        self._initialize_sensor()

    def _initialize_sensor(self):
        """初始化硬件连接"""
        try:
            # 懒加载依赖
            try:
                from smbus2 import SMBus  # type: ignore
                from sgp30 import Sgp30  # type: ignore
            except Exception as import_err:
                logger.warning(f"SGP30依赖缺失，传感器已禁用（Windows或无I2C环境可忽略）：{str(import_err)}")
                self.bus = None
                self.sensor = None
                self._available = False
                return

            if self.bus:
                try:
                    self.bus.close()
                except Exception:
                    pass

            self.bus = SMBus(self.bus_num)
            self.sensor = Sgp30(self.bus, baseline_filename=self.baseline_file)
            self.sensor.i2c_geral_call()
            self.sensor.init_sgp()

            if os.path.exists(self.baseline_file):
                self.sensor.load_baseline()

            self._available = True
            logger.info("SGP30传感器初始化成功")
        except Exception as e:
            logger.error(f"SGP30初始化失败: {str(e)}")
            self._available = False
            # 初始化失败不抛出，留给上层继续运行

    def _recover_sensor(self, retries=3):
        """异常恢复机制（仅在可用时尝试）"""
        if not self._available:
            return False
        for i in range(retries):
            try:
                time.sleep(2 ** i)  # 指数退避
                self._initialize_sensor()
                if self._available:
                    return True
            except Exception:
                continue
        self._available = False
        return False

    def get_co2(self):
        """
        获取CO2浓度读数(ppm)
        :return: int型CO2浓度值，如读取失败返回-1
        """
        try:
            if not self.sensor or not self._available:
                return -1

            measurements = self.sensor.read_measurements()
            co2 = measurements[0][0]

            if 400 <= co2 <= 10000:
                return co2
            else:
                # 读数异常时尝试内部恢复，但不抛出
                self._recover_sensor()
                return -1
        except Exception as e:
            self._log('error', f"读数失败: {str(e)}")
            self._recover_sensor()
            return -1

    def save_baseline(self):
        """手动保存当前校准基线"""
        try:
            if self.sensor and self._available:
                self.sensor.save_baseline()
                if self.log_manager:
                    self.log_manager.info("基线保存成功")
                return True
            return False
        except Exception as e:
            if self.log_manager:
                self.log_manager.warning(f"保存基线失败: {str(e)}")
            return False

    def is_available(self) -> bool:
        """返回传感器是否可用"""
        return bool(self._available)

    def __del__(self):
        """析构时关闭总线"""
        try:
            if self.bus:
                self.bus.close()
        except Exception:
            pass


# 测试代码
if __name__ == "__main__":
    reader = SGP30Reader()
    try:
        while True:
            co2 = reader.get_co2()
            print(f"Current CO2: {co2} ppm")
            time.sleep(10)
    except KeyboardInterrupt:
        reader.save_baseline()
        print("\nMeasurement stopped")