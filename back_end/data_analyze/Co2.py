import pandas as pd
import numpy as np
import os
import joblib
import lightgbm as lgb
from datetime import datetime, timedelta
from sklearn.preprocessing import OneHotEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import matplotlib.pyplot as plt

# 创建模型保存目录
os.makedirs('stu_models', exist_ok=True)


def generate_synthetic_data():
    """生成模拟数据集作为备用方案"""
    np.random.seed(42)
    base_date = datetime(2023, 1, 1)
    timestamps = [base_date + timedelta(minutes=30 * i) for i in range(1000)]
    area_ids = np.random.randint(2, 20, 1000)
    co2_levels = np.random.randint(300, 1200, 1000)

    return pd.DataFrame({
        'timestamp': timestamps,
        'terminal_id': area_ids,
        'co2_level': co2_levels
    })


def load_data():
    """加载数据，处理可能的异常"""
    try:
        # 尝试读取Excel文件
        df = pd.read_excel('webapi_co2data.xlsx')
        print("成功加载Excel数据")
        return df
    except Exception as e:
        print(f"读取Excel文件失败: {str(e)}")
        print("创建模拟数据...")
        return generate_synthetic_data()


def create_features(df):
    """创建时间特征和编码特征"""
    # 将时间戳转换为datetime格式
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # 提取时间特征
    df['hour'] = df['timestamp'].dt.hour
    df['minute'] = df['timestamp'].dt.minute
    df['minute_of_day'] = df['hour'] * 60 + df['minute']
    df['day_of_week'] = df['timestamp'].dt.dayofweek
    df['day_of_year'] = df['timestamp'].dt.dayofyear
    df['month'] = df['timestamp'].dt.month

    # 周期性编码
    df['time_sin'] = np.sin(2 * np.pi * df['minute_of_day'] / 1440)
    df['time_cos'] = np.cos(2 * np.pi * df['minute_of_day'] / 1440)
    df['week_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
    df['week_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)
    df['year_sin'] = np.sin(2 * np.pi * df['day_of_year'] / 365)
    df['year_cos'] = np.cos(2 * np.pi * df['day_of_year'] / 365)

    # 添加是否周末特征
    df['is_weekend'] = df['day_of_week'].apply(lambda x: 1 if x >= 5 else 0)

    return df


def encode_features(df):
    """对分类特征进行编码"""
    # 对day_of_week进行独热编码
    day_encoder = OneHotEncoder(
        categories=[list(range(7))],
        sparse_output=False,
        handle_unknown='ignore'
    )
    day_encoded = day_encoder.fit_transform(df[['day_of_week']])
    day_columns = [f'day_{i}' for i in range(7)]
    day_df = pd.DataFrame(day_encoded, columns=day_columns)

    # 对terminal_id进行独热编码
    terminal_ids = list(range(2, 20))
    terminal_encoder = OneHotEncoder(
        categories=[terminal_ids],
        sparse_output=False,
        handle_unknown='ignore'
    )
    terminal_encoded = terminal_encoder.fit_transform(df[['terminal_id']])
    terminal_columns = [f'terminal_{int(i)}' for i in terminal_encoder.categories_[0]]
    terminal_df = pd.DataFrame(terminal_encoded, columns=terminal_columns)

    # 合并编码结果
    df = pd.concat([df, day_df, terminal_df], axis=1)

    return df, day_encoder, terminal_encoder, day_columns, terminal_columns


def train_lightgbm(X, y):
    """训练LightGBM模型"""
    # 定义模型参数
    params = {
        'boosting_type': 'gbdt',
        'objective': 'regression',
        'metric': 'rmse',
        'num_leaves': 40,  # 增加叶子数量
        'learning_rate': 0.05,
        'feature_fraction': 0.8,
        'bagging_fraction': 0.8,
        'bagging_freq': 5,
        'min_child_samples': 20,  # 防止过拟合
        'verbosity': -1,
        'seed': 42,
        'n_jobs': -1  # 使用所有CPU核心
    }

    # 创建LightGBM数据集
    train_data = lgb.Dataset(X, label=y)

    # 训练模型
    print("开始训练LightGBM模型...")
    model = lgb.train(
        params,
        train_data,
        num_boost_round=200,
        valid_sets=[train_data],
        callbacks=[
            lgb.early_stopping(stopping_rounds=30),
            lgb.log_evaluation(period=50)
        ]
    )
    print("LightGBM模型训练完成")
    return model


def evaluate_model(model, X, y):
    """评估模型性能"""
    y_pred = model.predict(X)

    mae = mean_absolute_error(y, y_pred)
    rmse = np.sqrt(mean_squared_error(y, y_pred))
    r2 = r2_score(y, y_pred)

    print("\n===== 模型评估结果 =====")
    print(f"平均绝对误差 (MAE): {mae:.2f}")
    print(f"均方根误差 (RMSE): {rmse:.2f}")
    print(f"决定系数 (R²): {r2:.2f}")

    return mae, rmse, r2


def save_model(model, day_encoder, terminal_encoder, features, metrics):
    """保存模型和相关元数据"""
    pipeline = {
        'model': model,
        'day_encoder': day_encoder,
        'terminal_encoder': terminal_encoder,
        'feature_names': features
    }

    # 保存模型
    model_path = os.path.join('co2_models', 'lightgbm_model.pkl')
    joblib.dump(pipeline, model_path)
    print(f"模型已保存至: {model_path}")

    # 保存模型元数据 - 使用UTF-8编码避免字符问题
    with open(os.path.join('co2_models', 'model_info.txt'), 'w', encoding='utf-8') as f:
        f.write("CO2浓度预测模型信息\n")
        f.write("====================\n\n")
        f.write(f"模型类型: LightGBM\n")
        f.write(f"特征数量: {len(features)}\n")
        f.write(f"评估指标:\n")
        f.write(f"  MAE: {metrics['MAE']:.2f}\n")
        f.write(f"  RMSE: {metrics['RMSE']:.2f}\n")
        f.write(f"  R²: {metrics['R2']:.2f}\n")
        f.write("\n特征列表:\n")
        for feature in features:
            f.write(f"  - {feature}\n")

    print("模型元数据已保存至 co2_models/model_info.txt")


def main():
    """主函数"""
    print("===== CO2浓度预测模型训练 =====")

    # 1. 加载数据
    df = load_data()

    # 检查数据列
    print(f"数据列: {df.columns.tolist()}")

    # 2. 特征工程
    df = create_features(df)

    # 3. 特征编码
    df, day_encoder, terminal_encoder, day_columns, terminal_columns = encode_features(df)

    # 4. 准备特征和目标
    time_features = ['time_sin', 'time_cos', 'week_sin', 'week_cos', 'year_sin', 'year_cos', 'is_weekend']
    features = time_features + day_columns + terminal_columns
    X = df[features]
    y = df['co2_level']

    # 5. 划分训练集和测试集
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # 6. 训练模型
    model = train_lightgbm(X_train, y_train)

    # 7. 评估模型
    mae, rmse, r2 = evaluate_model(model, X_test, y_test)
    metrics = {'MAE': mae, 'RMSE': rmse, 'R2': r2}

    # 8. 保存模型
    save_model(model, day_encoder, terminal_encoder, features, metrics)

    print("\n模型训练和保存完成！")


if __name__ == "__main__":
    main()