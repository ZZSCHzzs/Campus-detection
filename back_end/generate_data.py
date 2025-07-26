#!/usr/bin/env python
"""
数据批量生成脚本
用于为校园检测系统生成测试数据，包括：
- 人数检测历史记录（绑定区域，仅id<=19）
- 温湿度数据记录（绑定区域，仅id<=19）
- CO2数据记录（绑定终端）
- 硬件节点数据更新（温湿度和检测字段）
"""

import os
import sys
import django
from datetime import datetime, timedelta
import random
import math
import pytz

# 设置Django环境
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'campus_detection.settings')
django.setup()

from webapi.models import Area, ProcessTerminal, HistoricalData, TemperatureHumidityData, CO2Data, HardwareNode
from django.utils import timezone

# 设置UTC+8时区
china_tz = pytz.timezone('Asia/Shanghai')


def generate_historical_data(days=30, records_per_day=48):
    """
    生成人数检测历史数据（绑定区域，仅id<=19）
    
    Args:
        days: 生成多少天的数据
        records_per_day: 每天多少条记录（默认每30分钟一条）
    """
    print(f"开始生成 {days} 天的人数检测历史数据（仅id<=19的区域）...")
    
    # 只获取id<=19的区域
    areas = Area.objects.filter(id__lte=19)
    if not areas:
        print("错误：没有找到id<=19的区域，请先创建区域数据")
        return
    
    total_records = 0
    # 使用UTC+8时区的当前时间
    now = timezone.now().astimezone(china_tz)
    
    for area in areas:
        print(f"为区域 '{area.name}' (ID: {area.id}) 生成数据...")
        
        for day in range(days):
            for record in range(records_per_day):
                # 计算时间戳（UTC+8时区）
                timestamp = now - timedelta(
                    days=days-day-1,
                    minutes=record * 30  # 每30分钟一条记录
                )
                
                # 根据区域特性和时间段生成人数
                hour = timestamp.hour
                area_factor = area.id % 5 + 1  # 区域特征因子
                
                # 基础人数（10-50）
                base_count = (10 + random.randint(0, 40)) * area_factor * 0.5
                
                # 高峰期调整（8-10点，17-19点）
                if 8 <= hour <= 10 or 17 <= hour <= 19:
                    base_count += (20 + random.randint(0, 30)) * (area_factor * 0.3)
                
                # 午休时间调整（12-14点）
                elif 12 <= hour <= 14:
                    base_count += (10 + random.randint(0, 19)) * (area_factor * 0.2)
                
                # 深夜时间调整（23-6点）
                elif hour >= 23 or hour <= 6:
                    base_count = max(5, int(base_count * 0.3))
                
                # 添加随机波动
                random_factor = 0.85 + random.random() * 0.3
                final_count = max(0, int(base_count * random_factor))
                
                # 创建记录
                HistoricalData.objects.create(
                    area=area,
                    detected_count=final_count,
                    timestamp=timestamp
                )
                total_records += 1
    
    print(f"成功生成 {total_records} 条人数检测历史记录")


def generate_temperature_humidity_data(days=30, records_per_day=48):
    """
    生成温湿度数据记录（绑定区域，仅id<=19）
    
    Args:
        days: 生成多少天的数据
        records_per_day: 每天多少条记录（默认每30分钟一条）
    """
    print(f"开始生成 {days} 天的温湿度数据（仅id<=19的区域）...")
    
    # 只获取id<=19的区域
    areas = Area.objects.filter(id__lte=19)
    if not areas:
        print("错误：没有找到id<=19的区域，请先创建区域数据")
        return
    
    total_records = 0
    # 使用UTC+8时区的当前时间
    now = timezone.now().astimezone(china_tz)
    
    for area in areas:
        print(f"为区域 '{area.name}' (ID: {area.id}) 生成温湿度数据...")
        
        for day in range(days):
            for record in range(records_per_day):
                # 计算时间戳（UTC+8时区）
                timestamp = now - timedelta(
                    days=days-day-1,
                    minutes=record * 30  # 每30分钟一条记录
                )
                
                # 根据区域和时间特性生成温湿度数据
                hour = timestamp.hour
                area_factor = area.id % 5 + 1
                
                # 温度生成（20-30°C，有日间变化）
                base_temp = 22 + (area_factor - 1) * 0.5
                if 10 <= hour <= 16:
                    base_temp += 3 + random.random() * 2  # 白天较热
                elif hour >= 18 or hour <= 6:
                    base_temp -= 1 + random.random() * 1  # 夜间较凉
                
                temperature = round(base_temp + (random.random() - 0.5) * 2, 1)
                
                # 湿度生成（30-80%，与温度反相关）
                humidity = 65 - (temperature - 22) * 2 + (random.random() - 0.5) * 10
                humidity = round(max(30, min(80, humidity)), 1)
                
                # 创建温湿度数据记录
                TemperatureHumidityData.objects.create(
                    area=area,
                    temperature=temperature,
                    humidity=humidity,
                    timestamp=timestamp
                )
                total_records += 1
    
    print(f"成功生成 {total_records} 条温湿度数据记录")


def generate_co2_data(days=30, records_per_day=48):
    """
    生成CO2数据记录（绑定终端）
    
    Args:
        days: 生成多少天的数据
        records_per_day: 每天多少条记录（默认每30分钟一条）
    """
    print(f"开始生成 {days} 天的CO2数据...")
    
    terminals = ProcessTerminal.objects.all()
    if not terminals:
        print("警告：系统中没有终端数据，无法生成CO2数据")
        return
    
    total_records = 0
    # 使用UTC+8时区的当前时间
    now = timezone.now().astimezone(china_tz)
    
    for terminal in terminals:
        print(f"为终端 '{terminal.name}' 生成CO2数据...")
        
        for day in range(days):
            for record in range(records_per_day):
                # 计算时间戳（UTC+8时区）
                timestamp = now - timedelta(
                    days=days-day-1,
                    minutes=record * 30  # 每30分钟一条记录
                )
                
                # 根据终端和时间特性生成CO2数据
                hour = timestamp.hour
                terminal_factor = terminal.id % 3 + 1
                
                # CO2生成（350-1200ppm，人员活动高峰期较高）
                base_co2 = 400 + terminal_factor * 50
                if (8 <= hour <= 10) or (17 <= hour <= 19):
                    base_co2 += 300 + random.randint(0, 200)  # 高峰期
                elif 12 <= hour <= 14:
                    base_co2 += 150 + random.randint(0, 100)  # 午休期
                elif hour >= 23 or hour <= 6:
                    base_co2 = max(350, int(base_co2 * 0.7))  # 夜间较低
                
                co2_level = max(350, int(base_co2 + (random.random() - 0.5) * 100))
                
                # 创建CO2数据记录
                CO2Data.objects.create(
                    terminal=terminal,
                    co2_level=co2_level,
                    timestamp=timestamp
                )
                total_records += 1
    
    print(f"成功生成 {total_records} 条CO2数据记录")


def update_hardware_nodes():
    """
    为所有硬件节点生成当前的温湿度和检测数据
    """
    print("开始更新所有硬件节点的温湿度和检测数据...")
    
    nodes = HardwareNode.objects.all()
    if not nodes:
        print("警告：系统中没有硬件节点数据")
        return
    
    # 使用UTC+8时区的当前时间
    now = timezone.now().astimezone(china_tz)
    hour = now.hour
    
    updated_count = 0
    
    for node in nodes:
        # 生成温度数据（20-30°C）
        node_factor = node.id % 5 + 1
        base_temp = 22 + (node_factor - 1) * 0.5
        
        # 根据时间调整温度
        if 10 <= hour <= 16:
            base_temp += 3 + random.random() * 2  # 白天较热
        elif hour >= 18 or hour <= 6:
            base_temp -= 1 + random.random() * 1  # 夜间较凉
        
        temperature = round(base_temp + (random.random() - 0.5) * 2, 1)
        
        # 生成湿度数据（30-80%，与温度反相关）
        humidity = 65 - (temperature - 22) * 2 + (random.random() - 0.5) * 10
        humidity = round(max(30, min(80, humidity)), 1)
        
        # 生成检测人数（根据时间段调整）
        base_count = (5 + random.randint(0, 20)) * node_factor * 0.3
        
        # 高峰期调整
        if 8 <= hour <= 10 or 17 <= hour <= 19:
            base_count += (10 + random.randint(0, 15)) * (node_factor * 0.2)
        elif 12 <= hour <= 14:
            base_count += (5 + random.randint(0, 10)) * (node_factor * 0.15)
        elif hour >= 23 or hour <= 6:
            base_count = max(0, int(base_count * 0.2))
        
        detected_count = max(0, int(base_count * (0.8 + random.random() * 0.4)))
        
        # 更新节点数据
        node.temperature = temperature
        node.humidity = humidity
        node.detected_count = detected_count
        node.status = True  # 设置为在线状态
        node.save()
        
        updated_count += 1
        print(f"更新节点 '{node.name}' (ID: {node.id}): 温度={temperature}°C, 湿度={humidity}%, 检测人数={detected_count}")
    
    print(f"成功更新 {updated_count} 个硬件节点的数据")


def clean_existing_data():
    """清理现有的测试数据"""
    historical_count = HistoricalData.objects.count()
    temp_humid_count = TemperatureHumidityData.objects.count()
    co2_count = CO2Data.objects.count()
    
    if historical_count > 0 or temp_humid_count > 0 or co2_count > 0:
        print(f"发现现有数据：")
        print(f"- 人数检测记录：{historical_count} 条")
        print(f"- 温湿度记录：{temp_humid_count} 条")
        print(f"- CO2记录：{co2_count} 条")
        
        response = input("是否清理现有数据？(y/N): ")
        if response.lower() == 'y':
            HistoricalData.objects.all().delete()
            TemperatureHumidityData.objects.all().delete()
            CO2Data.objects.all().delete()
            print("已清理现有数据")
        else:
            print("保留现有数据，将追加新数据")


def main():
    """主函数"""
    print("=" * 50)
    print("校园检测系统 - 数据生成脚本 (UTC+8时区)")
    print("=" * 50)
    
    # 检查区域和终端数据
    area_count = Area.objects.filter(id__lte=19).count()
    total_area_count = Area.objects.count()
    terminal_count = ProcessTerminal.objects.count()
    node_count = HardwareNode.objects.count()
    
    print(f"当前系统中有 {total_area_count} 个区域（其中id<=19的有 {area_count} 个），{terminal_count} 个终端，{node_count} 个硬件节点")
    
    if area_count == 0:
        print("警告：系统中没有id<=19的区域数据，无法生成人数检测和温湿度数据")
        print("请先运行区域生成脚本创建区域")
    
    if terminal_count == 0:
        print("警告：系统中没有终端数据，无法生成CO2数据")
        print("区域生成脚本会自动创建默认终端")
    
    if node_count == 0:
        print("警告：系统中没有硬件节点数据，无法更新节点信息")
    
    if area_count == 0 and terminal_count == 0 and node_count == 0:
        print("请先运行区域生成脚本：python generate_areas.py")
        return
    
    # 清理现有数据
    clean_existing_data()
    
    # 获取生成参数
    try:
        days = int(input("请输入要生成多少天的数据 (默认30天): ") or "30")
        records_per_day = int(input("请输入每天生成多少条记录 (默认48条，即每30分钟一条): ") or "48")
    except ValueError:
        print("输入无效，使用默认值：30天，每天48条记录")
        days = 30
        records_per_day = 48
    
    # 选择要生成的数据类型
    print(f"\n请选择要生成的数据类型：")
    print("1. 全部数据（人数检测 + 温湿度 + CO2 + 节点更新）")
    print("2. 仅人数检测数据（id<=19区域）")
    print("3. 仅温湿度数据（id<=19区域）")
    print("4. 仅CO2数据")
    print("5. 人数检测 + 温湿度（id<=19区域）")
    print("6. 仅更新硬件节点数据")
    
    choice = input("请选择 (1-6): ").strip() or "1"
    
    print(f"\n将生成 {days} 天的数据，每天 {records_per_day} 条记录（UTC+8时区）")
    
    # 计算总记录数
    total_historical = 0
    total_temp_humid = 0
    total_co2 = 0
    
    if choice in ['1', '2', '5']:
        total_historical = area_count * days * records_per_day
    if choice in ['1', '3', '5']:
        total_temp_humid = area_count * days * records_per_day
    if choice in ['1', '4']:
        total_co2 = terminal_count * days * records_per_day
    
    print(f"总计将生成：")
    if total_historical > 0:
        print(f"- 人数检测记录：{total_historical} 条（仅id<=19区域）")
    if total_temp_humid > 0:
        print(f"- 温湿度记录：{total_temp_humid} 条（仅id<=19区域）")
    if total_co2 > 0:
        print(f"- CO2记录：{total_co2} 条")
    if choice in ['1', '6']:
        print(f"- 硬件节点更新：{node_count} 个节点")
    
    confirm = input("\n确认开始生成？(y/N): ")
    if confirm.lower() != 'y':
        print("已取消生成")
        return
    
    # 开始生成数据
    start_time = datetime.now()
    
    try:
        # 根据选择生成数据
        if choice in ['1', '2', '5'] and area_count > 0:
            generate_historical_data(days, records_per_day)
        
        if choice in ['1', '3', '5'] and area_count > 0:
            generate_temperature_humidity_data(days, records_per_day)
        
        if choice in ['1', '4'] and terminal_count > 0:
            generate_co2_data(days, records_per_day)
        
        if choice in ['1', '6'] and node_count > 0:
            update_hardware_nodes()
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        print(f"\n" + "=" * 50)
        print("数据生成完成！")
        print(f"用时：{duration.total_seconds():.2f} 秒")
        print(f"最终统计：")
        print(f"- 人数检测记录：{HistoricalData.objects.count()} 条")
        print(f"- 温湿度记录：{TemperatureHumidityData.objects.count()} 条")
        print(f"- CO2记录：{CO2Data.objects.count()} 条")
        print(f"- 硬件节点：{HardwareNode.objects.count()} 个")
        print("=" * 50)
        
    except Exception as e:
        print(f"生成数据时出错：{e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()