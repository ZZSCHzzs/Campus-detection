#!/usr/bin/env python3
from smbus2 import SMBus
from sgp30 import Sgp30
import time
import json
import os


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

    def __init__(self, i2c_bus=1, baseline_file="sgp30_baseline.json"):
        """
        初始化传感器
        :param i2c_bus: I2C总线编号 (树莓派通常为1)
        :param baseline_file: 基线校准文件路径
        """
        self.bus_num = i2c_bus
        self.baseline_file = baseline_file
        self.bus = None
        self.sensor = None
        self._initialize_sensor()

    def _initialize_sensor(self):
        """初始化硬件连接"""
        try:
            if self.bus:
                self.bus.close()

            self.bus = SMBus(self.bus_num)
            self.sensor = Sgp30(self.bus, baseline_filename=self.baseline_file)
            self.sensor.i2c_geral_call()
            self.sensor.init_sgp()

            if os.path.exists(self.baseline_file):
                self.sensor.load_baseline()

        except Exception as e:
            print(f"Sensor init error: {str(e)}")
            self._recover_sensor()

    def _recover_sensor(self, retries=3):
        """异常恢复机制"""
        for i in range(retries):
            try:
                time.sleep(2 ** i)  # 指数退避
                self._initialize_sensor()
                return True
            except Exception:
                continue
        raise RuntimeError("Failed to recover sensor after retries")

    def get_co2(self):
        """
        获取CO2浓度读数(ppm)
        :return: int型CO2浓度值，如读取失败返回-1
        """
        try:
            if not self.sensor:
                self._initialize_sensor()

            measurements = self.sensor.read_measurements()
            co2 = measurements[0][0]

            # 数据有效性检查
            if 400 <= co2 <= 10000:  # 典型有效范围
                return co2
            else:
                self._recover_sensor()
                return self.get_co2()

        except Exception as e:
            print(f"Read error: {str(e)}")
            self._recover_sensor()
            return -1

    def save_baseline(self):
        """手动保存当前校准基线"""
        try:
            self.sensor.save_baseline()
            return True
        except Exception as e:
            print(f"Save baseline failed: {str(e)}")
            return False

    def __del__(self):
        """析构时关闭总线"""
        if self.bus:
            self.bus.close()


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