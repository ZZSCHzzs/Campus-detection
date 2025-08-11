import pandas as pd
import numpy as np
import os
from datetime import datetime
from sklearn.preprocessing import OneHotEncoder
from sklearn.ensemble import GradientBoostingRegressor
import joblib

# 创建模型保存目录
os.makedirs('stu_models', exist_ok=True)

# 1. 加载数据
# 这里假设您已经将数据文件放在当前目录下，名为'webapi_historicaldata.xls'
df = pd.read_excel('webapi_historicaldata.xls')

# 2. 特征工程
# 将时间戳转换为datetime格式
df['timestamp'] = pd.to_datetime(df['timestamp'])

# 提取时间特征（小时+分钟）
df['hour'] = df['timestamp'].dt.hour
df['minute'] = df['timestamp'].dt.minute
df['minute_of_day'] = df['hour'] * 60 + df['minute']  # 一天中的分钟数(0-1439)

# 周期性编码（处理时间循环性）
df['time_sin'] = np.sin(2 * np.pi * df['minute_of_day']/1440)
df['time_cos'] = np.cos(2 * np.pi * df['minute_of_day']/1440)

# 添加星期几特征
df['day_of_week'] = df['timestamp'].dt.dayofweek  # 周一=0, 周日=6

# 添加是否周末特征
df['is_weekend'] = df['day_of_week'].apply(lambda x: 1 if x >= 5 else 0)

# 对day_of_week进行独热编码 - 指定所有可能的类别
# 确保编码器包含所有可能的星期几（0-6）
day_encoder = OneHotEncoder(
    categories=[list(range(7))],  # 指定所有可能的类别
    sparse_output=False,
    handle_unknown='ignore'  # 忽略未知类别
)
day_encoded = day_encoder.fit_transform(df[['day_of_week']])
day_columns = [f'day_{i}' for i in range(7)]  # 固定为7列

# 创建包含独热编码结果的DataFrame
day_df = pd.DataFrame(day_encoded, columns=day_columns)
df = pd.concat([df, day_df], axis=1)

# 对area_id进行独热编码 - 指定所有可能的区域ID（2-19）
# 确保编码器包含所有可能的区域ID
area_ids = list(range(2, 20))  # 区域ID从2到19
area_encoder = OneHotEncoder(
    categories=[area_ids],  # 指定所有可能的类别
    sparse_output=False,
    handle_unknown='ignore'  # 忽略未知类别
)
area_encoded = area_encoder.fit_transform(df[['area_id']])
area_columns = [f'area_{int(i)}' for i in area_encoder.categories_[0]]

# 创建包含独热编码结果的DataFrame
area_df = pd.DataFrame(area_encoded, columns=area_columns)
df = pd.concat([df, area_df], axis=1)

# 3. 准备特征和目标变量
features = ['time_sin', 'time_cos', 'is_weekend'] + day_columns + area_columns
X = df[features]
y = df['detected_count']

# 4. 训练Gradient Boosting模型
model = GradientBoostingRegressor(
    n_estimators=200,
    learning_rate=0.05,
    max_depth=6,
    min_samples_split=5,
    min_samples_leaf=2,
    random_state=42
)
model.fit(X, y)

# 5. 保存整个预处理和建模pipeline到单个文件
pipeline = {
    'model': model,
    'day_encoder': day_encoder,
    'area_encoder': area_encoder,
    'feature_names': features
}

# 使用joblib保存模型
save_path = os.path.join('stu_models', 'gradient_boosting_model.kpl')
joblib.dump(pipeline, save_path)

print(f"模型已保存至: {save_path}")
print(f"使用特征: {features}")