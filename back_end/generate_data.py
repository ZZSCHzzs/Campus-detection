#!python
"""
数据批量生成脚本 - 复杂版
考虑季节、月份、节假日、时间段等多重影响因素
使用UTC+8时间
"""

import os
import sys
import django
from datetime import datetime, timedelta
import random
import math
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'campus_detection.settings')
# 设置Django环境
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'campus_detection.settings')
django.setup()

from webapi.models import Area, ProcessTerminal, HistoricalData, TemperatureHumidityData, CO2Data, HardwareNode

# 定义全局影响因素
class SeasonalFactors:
    """季节和月份影响因素"""

    @staticmethod
    def get_monthly_factor(month):
        """根据月份获取人数系数"""
        monthly_factors = {
            1: 0.2,  # 1月：寒假
            2: 0.1,  # 2月：寒假+春节
            3: 0.9,  # 3月：开学季
            4: 1.0,  # 4月：正常
            5: 1.0,  # 5月：正常+临近考试
            6: 1.3,  # 6月：考试月
            7: 0.4,  # 7月：暑假开始
            8: 0.3,  # 8月：暑假
            9: 1.2,  # 9月：开学+考研开始
            10: 1.5,  # 10月：考研强化
            11: 1.6,  # 11月：考研冲刺
            12: 1.4  # 12月：考试月
        }
        return monthly_factors.get(month, 1.0)

    @staticmethod
    def get_seasonal_temperature_factor(month):
        """根据月份获取温度季节性调整"""
        if month in [11, 12, 1, 2, 3]:  # 冬季
            return -5
        elif month in [6, 7, 8]:  # 夏季
            return +5
        elif month in [4, 5]:  # 春季
            return +2
        else:  # 秋季
            return -1

    @staticmethod
    def get_seasonal_humidity_factor(month):
        """根据月份获取湿度季节性调整"""
        if month in [6, 7, 8]:  # 夏季
            return +10
        elif month in [11, 12, 1, 2, 3]:  # 冬季
            return -10
        else:
            return 0


class TimeFactors:
    """时间段影响因素"""

    @staticmethod
    def get_hourly_people_factor(hour):
        """根据小时获取人数系数"""
        if 8 <= hour <= 9:  # 早上上课
            return 1.2
        elif 10 <= hour <= 11:  # 上午课程
            return 1.1
        elif 12 <= hour <= 13:  # 午餐时间
            return 0.3
        elif 14 <= hour <= 16:  # 下午课程
            return 1.0
        elif 17 <= hour <= 18:  # 晚餐时间
            return 0.3
        elif 19 <= hour <= 21:  # 晚自习/活动
            return 1.3
        elif 22 <= hour <= 23:  # 晚间休息
            return 0.6
        else:  # 深夜
            return 0.1

    @staticmethod
    def get_hourly_temperature_factor(hour):
        """根据小时获取温度系数"""
        if 10 <= hour <= 16:  # 白天较热
            return +2
        elif hour >= 22 or hour <= 6:  # 夜间较凉
            return -1
        else:
            return 0

    @staticmethod
    def get_weekend_factor(is_weekend):
        """周末影响系数"""
        return 0.6 if is_weekend else 1.0


class SpecialEvents:
    """特殊事件影响因素"""

    @staticmethod
    def is_holiday(date):
        """判断是否为节假日"""
        month_day = (date.month, date.day)
        holidays = {
            (1, 1): 0.3,  # 元旦
            (5, 1): 0.4,  # 劳动节
            (10, 1): 0.3,  # 国庆节
            (10, 2): 0.4,
            (10, 3): 0.5,
            (10, 4): 0.6,
            (10, 5): 0.7,
            (10, 6): 0.8,
            (10, 7): 0.9,
        }
        return holidays.get(month_day, 1.0)

    @staticmethod
    def is_exam_period(date):
        """判断是否为考试周"""
        month = date.month
        day = date.day
        if month == 6 and 10 <= day <= 30:
            return 1.2  # 6月考试周
        elif month == 12 and 15 <= day <= 31:
            return 1.3  # 12月考试周
        return 1.0


class AreaTypeFactors:
    """区域类型影响因素"""

    @staticmethod
    def get_area_type_factor(area_name):
        """根据区域名称判断区域类型系数"""
        area_name_lower = area_name.lower()

        if any(keyword in area_name_lower for keyword in ['食堂', '餐厅', 'cafe', '咖啡']):
            return ('dining', 2.0)
        elif any(keyword in area_name_lower for keyword in ['正心', '致知', 'lecture']):
            return ('classroom', 1.5)
        elif any(keyword in area_name_lower for keyword in ['图书馆']):
            return ('study', 1.8)
        elif any(keyword in area_name_lower for keyword in ['宿舍', 'dorm']):
            return ('dorm', 0.8)
        elif any(keyword in area_name_lower for keyword in ['实验室', 'lab']):
            return ('lab', 1.2)
        else:
            return ('other', 1.0)

    @staticmethod
    def get_area_time_factor(area_type, hour, is_weekend):
        """根据区域类型和时间获取系数"""
        if area_type == 'dining':
            if (11 <= hour <= 13) or (17 <= hour <= 19):
                return 2.5
            else:
                return 0.4
        elif area_type == 'classroom':
            if (8 <= hour <= 12) or (14 <= hour <= 18):
                return 1.8 if not is_weekend else 0.3
            else:
                return 0.5
        elif area_type == 'study':
            if (8 <= hour <= 22):
                return 2.0
            else:
                return 0.2
        elif area_type == 'dorm':
            if (20 <= hour <= 24) or (0 <= hour <= 8):
                return 1.5 if is_weekend else 1.2
            else:
                return 0.7
        elif area_type == 'lab':
            if (9 <= hour <= 18) and not is_weekend:
                return 1.5
            else:
                return 0.3
        else:
            return 1.0


def generate_historical_data(days=30, records_per_day=48):
    """生成人数检测历史数据（考虑多重影响因素）"""
    print(f"开始生成 {days} 天的人数检测历史数据（仅id<=19的区域）...")

    areas = Area.objects.filter(id__lte=19)
    if not areas:
        print("错误：没有找到id<=19的区域，请先创建区域数据")
        return

    total_records = 0
    # 使用UTC+8时间
    end_time = timezone.now() + timedelta(hours=8)
    start_time = end_time - timedelta(days=days)
    interval = timedelta(minutes=1440 / records_per_day)  # 每天均匀分布

    for area in areas:
        print(f"为区域 '{area.name}' (ID: {area.id}) 生成数据...")

        # 获取区域类型
        area_type, base_factor = AreaTypeFactors.get_area_type_factor(area.name)

        current_time = start_time
        while current_time < end_time:
            # 直接使用UTC+8时间
            local_time = current_time
            date = local_time.date()
            hour = local_time.hour
            weekday = local_time.weekday()
            is_weekend = weekday >= 5

            # 计算多重影响因子
            monthly_factor = SeasonalFactors.get_monthly_factor(date.month)
            hourly_factor = TimeFactors.get_hourly_people_factor(hour)
            weekend_factor = TimeFactors.get_weekend_factor(is_weekend)
            holiday_factor = SpecialEvents.is_holiday(date)
            exam_factor = SpecialEvents.is_exam_period(date)
            area_time_factor = AreaTypeFactors.get_area_time_factor(area_type, hour, is_weekend)

            # 基础人数（考虑区域基础系数）
            base_count = (20 + random.randint(0, 30)) * base_factor

            # 应用所有影响因素
            final_count = base_count * monthly_factor * hourly_factor * weekend_factor
            final_count *= holiday_factor * exam_factor * area_time_factor

            # 添加随机波动和区域特征
            area_specific_factor = (area.id % 5 + 1) * 0.3
            random_factor = 0.8 + random.random() * 0.4
            final_count = max(1, int(final_count * random_factor * area_specific_factor))

            # 创建记录（使用UTC+8时间）
            HistoricalData.objects.create(
                area=area,
                detected_count=final_count,
                timestamp=current_time
            )
            total_records += 1

            # 移动到下一个时间点
            current_time += interval

    print(f"成功生成 {total_records} 条人数检测历史记录")


def generate_temperature_humidity_data(days=30, records_per_day=48):
    """生成温湿度数据记录（考虑季节影响因素）"""
    print(f"开始生成 {days} 天的温湿度数据（仅id<=19的区域）...")

    areas = Area.objects.filter(id__lte=19)
    if not areas:
        print("错误：没有找到id<=19的区域，请先创建区域数据")
        return

    total_records = 0
    # 使用UTC+8时间
    end_time = timezone.now() + timedelta(hours=8)
    start_time = end_time - timedelta(days=days)
    interval = timedelta(minutes=1440 / records_per_day)

    for area in areas:
        print(f"为区域 '{area.name}' (ID: {area.id}) 生成温湿度数据...")

        current_time = start_time
        while current_time < end_time:
            # 直接使用UTC+8时间
            local_time = current_time
            date = local_time.date()
            hour = local_time.hour

            # 季节影响因素
            seasonal_temp = SeasonalFactors.get_seasonal_temperature_factor(date.month)
            seasonal_humid = SeasonalFactors.get_seasonal_humidity_factor(date.month)
            hourly_temp = TimeFactors.get_hourly_temperature_factor(hour)

            # 基础温度（考虑季节）
            base_temp = 22 + seasonal_temp + hourly_temp
            # 区域微调（不同区域可能有微小温差）
            area_temp_adjust = (area.id % 3 - 1) * 0.5

            temperature = round(base_temp + area_temp_adjust + (random.random() - 0.5) * 2, 1)

            # 湿度生成（考虑季节和与温度的反相关）
            base_humidity = 60 + seasonal_humid - (temperature - 22) * 1.5
            humidity = round(max(25, min(85, base_humidity + (random.random() - 0.5) * 10)), 1)

            # 特殊天气效果（偶尔出现极端天气）
            if random.random() < 0.02:
                if random.random() < 0.5:
                    temperature += random.choice([-5, -3, +5, +3])
                    humidity = random.choice([20, 25, 85, 90])
                else:
                    # 梅雨天气：高温高湿
                    temperature += 2
                    humidity += 15

            TemperatureHumidityData.objects.create(
                area=area,
                temperature=round(temperature, 1),
                humidity=round(humidity, 1),
                timestamp=current_time  # 使用UTC+8时间
            )
            total_records += 1

            current_time += interval

    print(f"成功生成 {total_records} 条温湿度数据记录")


def generate_co2_tvoc_data(days=30, records_per_day=48):
    """生成CO2和TVOC数据记录（考虑人员和环境因素）"""
    print(f"开始生成 {days} 天的CO2和TVOC数据...")

    terminals = ProcessTerminal.objects.all()
    if not terminals:
        print("警告：系统中没有终端数据，无法生成CO2和TVOC数据")
        return

    total_records = 0
    # 使用UTC+8时间
    end_time = timezone.now() + timedelta(hours=8)
    start_time = end_time - timedelta(days=days)
    interval = timedelta(minutes=1440 / records_per_day)

    for terminal in terminals:
        print(f"为终端 '{terminal.name}' 生成CO2和TVOC数据...")

        current_time = start_time
        while current_time < end_time:
            # 直接使用UTC+8时间
            local_time = current_time
            date = local_time.date()
            hour = local_time.hour
            is_weekend = local_time.weekday() >= 5

            # 获取相关的影响因子
            monthly_factor = SeasonalFactors.get_monthly_factor(date.month)
            hourly_factor = TimeFactors.get_hourly_people_factor(hour)
            weekend_factor = TimeFactors.get_weekend_factor(is_weekend)

            # 人员密度影响（假设与人数因子相关）
            people_density = monthly_factor * hourly_factor * weekend_factor

            # CO2生成（350-2000ppm，与人员密度强相关）
            base_co2 = 400 + (people_density * 300)
            co2_level = max(350, min(2000, int(base_co2 + (random.random() - 0.5) * 100)))

            # TVOC生成（0.1-3.0mg/m³，与CO2和季节相关）
            base_tvoc = 0.3 + (people_density * 0.5)
            # 夏季TVOC更容易挥发
            seasonal_tvoc_factor = 1.2 if date.month in [6, 7, 8] else 1.0
            tvoc_level = round(max(0.1, min(3.0, base_tvoc * seasonal_tvoc_factor + (random.random() - 0.5) * 0.3)), 2)

            # 通风效果影响（工作时间通风好）
            if (8 <= hour <= 18) and not is_weekend:
                co2_level = int(co2_level * 0.8)
                tvoc_level = round(tvoc_level * 0.7, 2)

            # 异常值检测（设备故障或特殊事件）
            is_extreme = random.random() < 0.008
            if is_extreme:
                if random.random() < 0.6:
                    co2_level = 1800 + random.randint(0, 500)
                    tvoc_level = round(2.5 + random.random() * 1.0, 2)
                else:
                    co2_level = 300 + random.randint(0, 50)
                    tvoc_level = round(0.1 + random.random() * 0.1, 2)

            CO2Data.objects.create(
                terminal=terminal,
                co2_level=co2_level,
                tvoc_level=tvoc_level,
                timestamp=current_time  # 使用UTC+8时间
            )
            total_records += 1

            current_time += interval

    print(f"成功生成 {total_records} 条CO2和TVOC数据记录")


def update_hardware_nodes():
    """为所有硬件节点生成当前的温湿度和检测数据"""
    print("开始更新所有硬件节点的温湿度和检测数据...")

    nodes = HardwareNode.objects.all()
    if not nodes:
        print("警告：系统中没有硬件节点数据")
        return

    # 使用UTC+8时间
    now = timezone.now() + timedelta(hours=8)
    # 直接使用UTC+8时间
    hour = now.hour
    date = now.date()
    is_weekend = now.weekday() >= 5

    updated_count = 0

    for node in nodes:
        # 获取季节和时间影响因素
        monthly_factor = SeasonalFactors.get_monthly_factor(date.month)
        hourly_factor = TimeFactors.get_hourly_people_factor(hour)
        weekend_factor = TimeFactors.get_weekend_factor(is_weekend)
        seasonal_temp = SeasonalFactors.get_seasonal_temperature_factor(date.month)
        seasonal_humid = SeasonalFactors.get_seasonal_humidity_factor(date.month)

        # 温度生成
        base_temp = 22 + seasonal_temp
        if 10 <= hour <= 16:
            base_temp += 3 + random.random() * 2
        elif hour >= 18 or hour <= 6:
            base_temp -= 1 + random.random() * 1

        temperature = round(base_temp + (random.random() - 0.5) * 2, 1)

        # 湿度生成
        humidity = 65 + seasonal_humid - (temperature - 22) * 2 + (random.random() - 0.5) * 10
        humidity = round(max(25, min(85, humidity)), 1)

        # 人数检测（考虑所有影响因素）
        base_count = (10 + random.randint(0, 20)) * (node.id % 5 + 1) * 0.3
        detected_count = max(1, int(base_count * monthly_factor * hourly_factor * weekend_factor * (0.8 + random.random() * 0.4)))

        # 更新节点数据
        node.temperature = temperature
        node.humidity = humidity
        node.detected_count = detected_count
        node.status = True
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
    print("=" * 60)
    print("校园检测系统 - 复杂数据生成脚本 (UTC+8时间)")
    print("考虑季节、月份、节假日、时间段等多重影响因素")
    print("=" * 60)

    # 检查区域和终端数据
    area_count = Area.objects.filter(id__lte=19).count()
    total_area_count = Area.objects.count()
    terminal_count = ProcessTerminal.objects.count()
    node_count = HardwareNode.objects.count()

    print(f"当前系统中有 {total_area_count} 个区域（其中id<=19的有 {area_count} 个）")
    print(f"{terminal_count} 个终端，{node_count} 个硬件节点")

    if area_count == 0:
        print("警告：系统中没有id<=19的区域数据，无法生成人数检测和温湿度数据")

    if terminal_count == 0:
        print("警告：系统中没有终端数据，无法生成CO2和TVOC数据")

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
    print("1. 全部数据（人数检测 + 温湿度 + CO2/TVOC + 节点更新）")
    print("2. 仅人数检测数据（id<=19区域）")
    print("3. 仅温湿度数据（id<=19区域）")
    print("4. 仅CO2/TVOC数据")
    print("5. 人数检测 + 温湿度（id<=19区域）")
    print("6. 仅更新硬件节点数据")

    choice = input("请选择 (1-6): ").strip() or "1"

    print(f"\n将生成 {days} 天的数据，每天 {records_per_day} 条记录（UTC+8时间）")
    print("注：数据生成考虑了季节、月份、节假日、时间段等多重影响因素")

    # 计算总记录数
    total_historical = 0
    total_temp_humid = 0
    total_co2_tvoc = 0

    if choice in ['1', '2', '5'] and area_count > 0:
        total_historical = area_count * days * records_per_day
    if choice in ['1', '3', '5'] and area_count > 0:
        total_temp_humid = area_count * days * records_per_day
    if choice in ['1', '4'] and terminal_count > 0:
        total_co2_tvoc = terminal_count * days * records_per_day

    print(f"\n总计将生成：")
    if total_historical > 0:
        print(f"- 人数检测记录：{total_historical} 条（考虑多重影响因素）")
    if total_temp_humid > 0:
        print(f"- 温湿度记录：{total_temp_humid} 条（考虑季节影响因素）")
    if total_co2_tvoc > 0:
        print(f"- CO2/TVOC记录：{total_co2_tvoc} 条（考虑人员密度影响）")
    if choice in ['1', '6']:
        print(f"- 硬件节点更新：{node_count} 个节点")

    confirm = input("\n确认开始生成？(y/N): ")
    if confirm.lower() != 'y':
        print("已取消生成")
        return

    # 开始生成数据
    start_time = datetime.now()

    try:
        if choice in ['1', '2', '5'] and area_count > 0:
            generate_historical_data(days, records_per_day)

        if choice in ['1', '3', '5'] and area_count > 0:
            generate_temperature_humidity_data(days, records_per_day)

        if choice in ['1', '4'] and terminal_count > 0:
            generate_co2_tvoc_data(days, records_per_day)

        if choice in ['1', '6'] and node_count > 0:
            update_hardware_nodes()

        end_time = datetime.now()
        duration = end_time - start_time

        print(f"\n" + "=" * 60)
        print("数据生成完成！")
        print(f"用时：{duration.total_seconds():.2f} 秒")
        print(f"最终统计：")
        print(f"- 人数检测记录：{HistoricalData.objects.count()} 条")
        print(f"- 温湿度记录：{TemperatureHumidityData.objects.count()} 条")
        print(f"- CO2/TVOC记录：{CO2Data.objects.count()} 条")
        print(f"- 硬件节点：{HardwareNode.objects.count()} 个")
        print("=" * 60)

    except Exception as e:
        print(f"生成数据时出错：{e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()