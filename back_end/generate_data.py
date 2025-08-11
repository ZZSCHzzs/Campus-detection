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
import pytz
from django.utils import timezone
import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import train_test_split
import joblib

# 设置Django环境
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'campus_detection.settings')
django.setup()

from webapi.models import Area, ProcessTerminal, HistoricalData, TemperatureHumidityData, CO2Data, HardwareNode

# 设置UTC+8时区
china_tz = pytz.timezone('Asia/Shanghai')


def generate_historical_data(days=30, records_per_day=48):
    """
    生成人数检测历史数据（绑定区域，仅id<=19）
    使用训练好的梯度提升模型进行预测

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

    # 加载训练好的模型
    model_path = os.path.join('data_analyze','stu_models', 'gradient_boosting_model.kpl')
    if not os.path.exists(model_path):
        print(f"错误：模型文件不存在: {model_path}")
        return

    try:
        pipeline = joblib.load(model_path)
        model = pipeline['model']
        day_encoder = pipeline['day_encoder']
        area_encoder = pipeline['area_encoder']
        feature_names = pipeline['feature_names']
        print("成功加载梯度提升模型")
    except Exception as e:
        print(f"加载模型失败: {str(e)}")
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
                    days=days - day - 1,
                    minutes=record * 30  # 每30分钟一条记录
                )

                # 准备特征数据
                hour = timestamp.hour
                minute = timestamp.minute
                minute_of_day = hour * 60 + minute

                # 计算时间特征
                time_sin = np.sin(2 * np.pi * minute_of_day / 1440)
                time_cos = np.cos(2 * np.pi * minute_of_day / 1440)

                # 星期几特征
                day_of_week = timestamp.weekday()  # 周一=0, 周日=6
                is_weekend = 1 if day_of_week >= 5 else 0

                # 创建特征字典
                features = {
                    'time_sin': time_sin,
                    'time_cos': time_cos,
                    'is_weekend': is_weekend,
                    'day_of_week': day_of_week,
                    'area_id': area.id
                }

                # 转换为DataFrame
                input_df = pd.DataFrame([features])

                # 应用编码器 - 使用编码器的实际类别数
                day_encoded = day_encoder.transform(input_df[['day_of_week']])
                day_columns = [f'day_{i}' for i in range(day_encoded.shape[1])]
                for i, col in enumerate(day_columns):
                    input_df[col] = day_encoded[:, i]

                area_encoded = area_encoder.transform(input_df[['area_id']])
                area_columns = [f'area_{int(i)}' for i in area_encoder.categories_[0]]
                for i, col in enumerate(area_columns):
                    input_df[col] = area_encoded[:, i]

                # 确保特征顺序与训练时一致
                X_new = input_df[feature_names]

                # 使用模型预测人数
                detected_count = model.predict(X_new)[0]

                # 确保人数是非负整数,限制在200以内
                detected_count = max(0, int(round(detected_count)))
                detected_count = min(150, int(round(detected_count)))
                # 创建记录
                HistoricalData.objects.create(
                    area=area,
                    detected_count=detected_count,
                    timestamp=timestamp
                )
                total_records += 1

    print(f"成功生成 {total_records} 条人数检测历史记录")


def generate_temperature_humidity_data(days=30, records_per_day=48):
    # 1. 加载模型（仅一次）
    model_temp = joblib.load('data_analyze/models/temperature_model.pkl')
    model_humid = joblib.load('data_analyze/models/humidity_model.pkl')
    feature_info = joblib.load('data_analyze/models/feature_info.pkl')

    # 2. 生成所有时间戳
    now = timezone.now().astimezone(china_tz)
    timestamps = [now - timedelta(days=d, minutes=m)
                  for d in range(days)
                  for m in range(0, 1440, 1440 // records_per_day)]

    # 3. 获取区域数据
    areas = Area.objects.filter(id__lte=19)
    if not areas:
        print("警告：没有找到id<=19的区域")
        return

    # 4. 构造批量输入数据
    input_data = []
    for area in areas:
        for ts in timestamps:
            # 时间特征
            hour = ts.hour
            minute = ts.minute
            day_of_week = ts.weekday()
            day_of_month = ts.day
            month = ts.month

            # 季节特征
            season = 'winter' if month in [11, 12, 1, 2, 3] else \
                'spring' if month in [4, 5] else \
                    'summer' if month in [6, 7, 8] else 'autumn'

            # 构造特征行
            row = {
                'hour': hour,
                'minute': minute,
                'day_of_week': day_of_week,
                'day_of_month': day_of_month,
                'month': month,
                'area_id': area.id
            }

            # 添加独热编码
            for col in feature_info['season_columns']:
                row[col] = 1.0 if col.endswith(season) else 0.0
            for col in feature_info['area_columns']:
                row[col] = 1.0 if col.endswith(str(area.id)) else 0.0

            input_data.append(row)

    # 5. 转换为DataFrame并预测
    input_df = pd.DataFrame(input_data)
    X = input_df[feature_info['feature_names']]
    temp_preds = model_temp.predict(X)
    humid_preds = model_humid.predict(X)

    # 6. 根据季节调整预测值（哈尔滨气候特点）
    adjusted_temp_preds = []
    adjusted_humid_preds = []

    # 哈尔滨季节调整系数（基于气候数据）
    season_adjustments = {
        'winter': {'temp_offset': -20, 'temp_scale': 0.7, 'humid_offset': -30, 'humid_scale': 0.6},
        'spring': {'temp_offset': -5, 'temp_scale': 0.9, 'humid_offset': -10, 'humid_scale': 0.8},
        'summer': {'temp_offset': 0, 'temp_scale': 1.0, 'humid_offset': 0, 'humid_scale': 1.0},
        'autumn': {'temp_offset': -8, 'temp_scale': 0.85, 'humid_offset': -15, 'humid_scale': 0.75}
    }

    for i, row in input_df.iterrows():
        # 确定季节
        month = row['month']
        season = 'winter' if month in [11, 12, 1, 2, 3] else \
            'spring' if month in [4, 5] else \
                'summer' if month in [6, 7, 8] else 'autumn'

        # 获取调整参数
        adj = season_adjustments[season]

        # 调整温度
        temp = temp_preds[i]
        adjusted_temp = (temp * adj['temp_scale']) + adj['temp_offset']

        # 调整湿度
        humid = humid_preds[i]
        adjusted_humid = (humid * adj['humid_scale']) + adj['humid_offset']

        # 确保湿度在合理范围内
        adjusted_humid = max(20, min(adjusted_humid, 95))

        adjusted_temp_preds.append(adjusted_temp)
        adjusted_humid_preds.append(adjusted_humid)

    # 7. 批量保存到数据库
    records = []
    for i, row in input_df.iterrows():
        # 使用调整后的值
        temp = adjusted_temp_preds[i]
        humid = adjusted_humid_preds[i]

        # 获取时间戳索引
        ts_index = i % len(timestamps)

        records.append(TemperatureHumidityData(
            area_id=row['area_id'],
            temperature=temp,
            humidity=humid,
            timestamp=timestamps[ts_index]
        ))

    TemperatureHumidityData.objects.bulk_create(records)

    print(f"成功生成 {len(records)} 条温湿度数据")



def generate_co2_data(days=30, records_per_day=48):
    """
    生成CO2数据记录（绑定终端），使用LightGBM模型预测CO2浓度
    增加哈尔滨工业大学特有的影响因素：人数、气温、冬季燃煤取暖等

    Args:
        days: 生成多少天的数据
        records_per_day: 每天多少条记录（默认每30分钟一条）
    """
    print(f"开始生成 {days} 天的CO2数据（哈尔滨工业大学）...")

    # 加载训练好的模型
    model_path = os.path.join('data_analyze', 'co2_models', 'lightgbm_model.pkl')
    if not os.path.exists(model_path):
        print(f"错误：模型文件不存在: {model_path}")
        return

    try:
        pipeline = joblib.load(model_path)
        model = pipeline['model']
        day_encoder = pipeline['day_encoder']
        terminal_encoder = pipeline['terminal_encoder']
        feature_names = pipeline['feature_names']

    except Exception as e:
        print(f"加载模型失败: {str(e)}")
        return

    terminals = ProcessTerminal.objects.all()
    if not terminals:
        print("警告：系统中没有终端数据，无法生成CO2数据")
        return

    total_records = 0
    # 使用UTC+8时区的当前时间
    now = timezone.now().astimezone(china_tz)


    def get_hit_factors(timestamp):
        """获取哈尔滨工业大学特有的影响因素"""
        month = timestamp.month
        hour = timestamp.hour
        day_of_week = timestamp.weekday()

        # 1. 人数影响因子（基于时间）
        # 上课时间
        if (8 <= hour <= 12) or (14 <= hour <= 18):
            people_factor = 1.2 + (random.random() * 0.2)  # 增加20-40%

        elif 19 <= hour <= 22:
            people_factor = 1.1 + (random.random() * 0.1)  # 增加10-20%
        # 深夜和凌晨
        elif hour >= 23 or hour <= 6:
            people_factor = 0.7 + (random.random() * 0.1)  # 减少30-20%
        else:
            people_factor = 1.0

        # 2. 气温影响因子（基于月份）
        # 哈尔滨气温特点：冬季寒冷，夏季温暖
        if month in [12, 1, 2]:  # 冬季
            temp_factor = 1.3 + (random.random() * 0.2)  # 增加30-50%
        elif month in [6, 7, 8]:  # 夏季
            temp_factor = 0.9 + (random.random() * 0.1)  # 减少10-0%
        else:  # 春秋季
            temp_factor = 1.0

        # 3. 冬季燃煤取暖影响（11月-3月）
        heating_factor = 1.0
        if month in [11, 12, 1, 2, 3]:
            # 供暖时间（早6点-晚10点）
            if 6 <= hour <= 22:
                heating_factor = 1.2 + (random.random() * 0.1)  # 增加20-30%

        # 4. 考试周影响（假设每月最后一周为考试周）
        exam_factor = 1.0
        if timestamp.day > 25:  # 每月最后几天
            # 考试周自习人数增加
            if (8 <= hour <= 12) or (14 <= hour <= 22):
                exam_factor = 1.15 + (random.random() * 0.1)  # 增加15-25%

        # 5. 假期影响（寒暑假）
        holiday_factor = 1.0
        # 寒假（1月-2月）
        if month in [1, 2]:
            holiday_factor = 0.7 + (random.random() * 0.1)  # 减少30-20%
        # 暑假（7月-8月）
        elif month in [7, 8]:
            holiday_factor = 0.8 + (random.random() * 0.1)  # 减少20-10%

        # 6. 周末影响
        weekend_factor = 1.0
        if day_of_week >= 5:  # 周六、周日
            if 8 <= hour <= 18:  # 白天
                weekend_factor = 0.8 + (random.random() * 0.1)  # 减少20-10%
            elif 19 <= hour <= 22:  # 晚上
                weekend_factor = 1.1 + (random.random() * 0.1)  # 增加10-20%

        # 综合影响因子
        combined_factor = people_factor * temp_factor * heating_factor * exam_factor * holiday_factor * weekend_factor

        return combined_factor

    for terminal in terminals:
        print(f"为终端 '{terminal.name}' 生成CO2数据...")

        for day in range(days):
            for record in range(records_per_day):
                # 计算时间戳（UTC+8时区）
                timestamp = now - timedelta(
                    days=days - day - 1,
                    minutes=record * 30  # 每30分钟一条记录
                )

                # 准备特征数据
                hour = timestamp.hour
                minute = timestamp.minute
                minute_of_day = hour * 60 + minute
                day_of_week = timestamp.weekday()
                day_of_year = timestamp.timetuple().tm_yday

                # 计算时间特征
                time_sin = np.sin(2 * np.pi * minute_of_day / 1440)
                time_cos = np.cos(2 * np.pi * minute_of_day / 1440)
                week_sin = np.sin(2 * np.pi * day_of_week / 7)
                week_cos = np.cos(2 * np.pi * day_of_week / 7)
                year_sin = np.sin(2 * np.pi * day_of_year / 365)
                year_cos = np.cos(2 * np.pi * day_of_year / 365)
                is_weekend = 1 if day_of_week >= 5 else 0

                # 创建特征字典
                features = {
                    'time_sin': time_sin,
                    'time_cos': time_cos,
                    'week_sin': week_sin,
                    'week_cos': week_cos,
                    'year_sin': year_sin,
                    'year_cos': year_cos,
                    'is_weekend': is_weekend,
                    'day_of_week': day_of_week,
                    'terminal_id': terminal.id
                }

                # 转换为DataFrame
                input_df = pd.DataFrame([features])

                # 应用编码器
                day_encoded = day_encoder.transform(input_df[['day_of_week']])
                for i in range(7):
                    input_df[f'day_{i}'] = day_encoded[:, i]

                terminal_encoded = terminal_encoder.transform(input_df[['terminal_id']])
                terminal_columns = [f'terminal_{int(i)}' for i in terminal_encoder.categories_[0]]
                for i, col in enumerate(terminal_columns):
                    input_df[col] = terminal_encoded[:, i]

                # 确保特征顺序与训练时一致
                X_new = input_df[feature_names]

                # 使用模型预测CO2浓度
                co2_level = model.predict(X_new)[0]

                # 应用哈尔滨工业大学特有的影响因素
                hit_factor = get_hit_factors(timestamp)
                co2_level *= hit_factor

                # 确保CO2浓度在合理范围内
                co2_level = max(350, min(1500, int(co2_level)))

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
    使用机器学习模型更新硬件节点数据（基于区域绑定关系）
    改进点：
    1. 优先使用节点直接绑定的区域（bound_node_id）
    2. 兼容终端关联的区域（terminal.area）
    3. 提供默认区域后备
    """
    print("=" * 50)
    print("开始执行硬件节点数据更新（基于区域绑定关系）")
    print("=" * 50)

    # 时区设置
    china_tz = pytz.timezone('Asia/Shanghai')
    now = timezone.now().astimezone(china_tz)

    # 1. 加载机器学习模型 =============================================
    print("\n加载机器学习模型...")
    try:
        # 人数预测模型
        hist_model_path = os.path.join('data_analyze', 'stu_models', 'gradient_boosting_model.kpl')
        hist_pipeline = joblib.load(hist_model_path)
        hist_model = hist_pipeline['model']
        hist_day_encoder = hist_pipeline['day_encoder']
        hist_area_encoder = hist_pipeline['area_encoder']
        hist_feature_names = hist_pipeline['feature_names']

        # 温湿度预测模型
        temp_model = joblib.load('data_analyze/models/temperature_model.pkl')
        humid_model = joblib.load('data_analyze/models/humidity_model.pkl')
        feature_info = joblib.load('data_analyze/models/feature_info.pkl')

        print("✅ 模型加载成功")
    except Exception as e:
        print(f"❌ 模型加载失败: {str(e)}")
        return

    # 2. 获取默认区域 ================================================
    default_area = Area.objects.filter(id__lte=19).first()
    if not default_area:
        print("❌ 错误：系统中没有id<=19的区域")
        return

    # 3. 准备特征工程函数 ============================================
    def prepare_hist_features(area_id, timestamp):
        """准备人数预测特征"""
        hour = timestamp.hour
        minute = timestamp.minute
        minute_of_day = hour * 60 + minute
        day_of_week = timestamp.weekday()

        features = {
            'time_sin': np.sin(2 * np.pi * minute_of_day / 1440),
            'time_cos': np.cos(2 * np.pi * minute_of_day / 1440),
            'is_weekend': 1 if day_of_week >= 5 else 0,
            'day_of_week': day_of_week,
            'area_id': area_id
        }

        df = pd.DataFrame([features])

        # 应用编码器
        day_encoded = hist_day_encoder.transform(df[['day_of_week']])
        for i in range(day_encoded.shape[1]):
            df[f'day_{i}'] = day_encoded[:, i]

        area_encoded = hist_area_encoder.transform(df[['area_id']])
        area_columns = [f'area_{int(i)}' for i in hist_area_encoder.categories_[0]]
        for i, col in enumerate(area_columns):
            df[col] = area_encoded[:, i]

        return df[hist_feature_names]

    def prepare_temp_humid_features(area_id, timestamp, node_id=None):
        """准备温湿度预测特征（新增node_id参数）"""
        month = timestamp.month
        season = 'winter' if month in [11, 12, 1, 2, 3] else \
            'spring' if month in [4, 5] else \
                'summer' if month in [6, 7, 8] else 'autumn'

        features = {
            'hour': timestamp.hour,
            'minute': timestamp.minute,
            'day_of_week': timestamp.weekday(),
            'day_of_month': timestamp.day,
            'month': month,
            'area_id': area_id,
            'season': season,
            'node_id': node_id % 10 if node_id else 0  # 使用节点ID作为特征
        }

        df = pd.DataFrame([features])

        # 应用编码器
        for col in feature_info.get('season_columns', []):
            season_name = col.split('_')[1]
            df[col] = 1.0 if season_name == season else 0.0

        for col in feature_info.get('area_columns', []):
            col_id = int(col.split('_')[1])
            df[col] = 1.0 if col_id == area_id else 0.0

        return df[feature_info['feature_names']]

    # 4. 哈尔滨气候调整函数 ==========================================
    def apply_harbin_adjustment(temp, humid, month):
        """应用哈尔滨特有的气候调整"""
        # 冬季调整（11月-3月）
        if month in [11, 12, 1, 2, 3]:
            temp = temp * 0.6 - 10  # 温度降低
            humid = humid * 0.5 - 15  # 湿度降低
        # 夏季调整（6月-8月）
        elif month in [6, 7, 8]:
            temp = temp * 1.1 + 2  # 温度升高
            humid = humid * 1.1 + 10  # 湿度升高

        return temp, humid

    # 5. 更新所有硬件节点 ===========================================
    nodes = HardwareNode.objects.all()
    if not nodes:
        print("⚠️ 系统中没有硬件节点数据")
        return

    print(f"\n开始更新 {len(nodes)} 个硬件节点...")

    for node in nodes:
        try:
            # === 核心改进：动态获取区域 ===
            # 方案1：优先使用节点直接绑定的区域（通过Area.bound_node_id）
            area = Area.objects.filter(bound_node_id=node.id).first()
            area_source = "节点绑定区域"

            # 方案2：如果没有绑定区域，尝试通过终端获取
            if not area and hasattr(node, 'terminal') and node.terminal:
                area = node.terminal.area
                area_source = "终端关联区域"

            # 方案3：如果仍然没有区域，使用默认区域
            if not area:
                area = default_area
                area_source = "默认区域"
                print(f"⚠️ 节点 {node.name} 未绑定区域，使用默认区域: {area.name}")

            # === 生成差异化时间戳 ===
            node_time = now - timedelta(minutes=node.id % 60)  # 按节点ID偏移时间

            # === 使用模型预测 ===
            hist_features = prepare_hist_features(area.id, node_time)
            temp_humid_features = prepare_temp_humid_features(area.id, node_time, node.id)

            # 预测原始值
            detected_count = hist_model.predict(hist_features)[0]
            temperature = temp_model.predict(temp_humid_features)[0]
            humidity = humid_model.predict(temp_humid_features)[0]

            # 应用哈尔滨调整
            temperature, humidity = apply_harbin_adjustment(temperature, humidity, now.month)

            # 添加随机扰动（防止数据完全一致）
            temperature += round(random.uniform(-0.3, 0.3), 1)
            humidity += round(random.uniform(-2, 2), 1)
            detected_count += random.randint(-1, 1)

            # 确保数据合理性
            detected_count = max(0, min(200, int(detected_count)))
            temperature = round(max(-20, min(40, temperature)), 1)
            humidity = round(max(15, min(95, humidity)), 1)

            # 更新节点
            node.temperature = temperature
            node.humidity = humidity
            node.detected_count = detected_count
            node.timestamp = now
            node.status = True
            node.save()

            print(f"🔄 更新节点 {node.name} ({area_source}[{area.name}]): "
                  f"温度={temperature}°C, 湿度={humidity}%, 人数={detected_count}")

        except Exception as e:
            print(f"❌ 更新节点 {node.name} 失败: {str(e)}")
            continue

    print("\n" + "=" * 50)
    print(f"✅ 硬件节点更新完成！共更新 {len(nodes)} 个节点")
    print(f"更新时间: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print("=" * 50)


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

    print(
        f"当前系统中有 {total_area_count} 个区域（其中id<=19的有 {area_count} 个），{terminal_count} 个终端，{node_count} 个硬件节点")

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
