import requests
import cv2

camera_config = {
    # 分辨率 (Resolution): 摄像头的分辨率大小，越大图像越清晰。可选值如下：
    # 10: UXGA(1600x1200), 9: SXGA(1280x1024), 8: XGA(1024x768),
    # 7: SVGA(800x600), 6: VGA(640x480), 5: CIF(400x296) (默认),
    # 4: QVGA(320x240), 3: HQVGA(240x176), 0: QQVGA(160x120)
    'framesize': 8,

    # 质量 (Quality): 图像压缩质量。值越高，压缩越强，图像质量越差。范围: 10 (低压缩, 高质量) - 63 (高压缩, 低质量)
    'quality': 10,

    # 亮度 (Brightness): 调整图像的亮度。范围: -2 (最暗) 到 2 (最亮)，默认值为 0 (标准亮度)
    'brightness': 1,

    # 对比度 (Contrast): 调整图像对比度。范围: -2 (最小对比度) 到 2 (最大对比度)，默认值为 0 (标准对比度)
    'contrast': 0,

    # 饱和度 (Saturation): 调整图像的饱和度。范围: -2 (低饱和度) 到 2 (高饱和度)，默认值为 0 (标准饱和度)
    'saturation': 0,

    # 特殊效果 (Special Effect): 图像的特殊效果。可选值如下：
    # 0: 无效果 (默认), 1: 负片, 2: 灰度, 3: 红色滤镜,
    # 4: 绿色滤镜, 5: 蓝色滤镜, 6: 棕色复古效果
    'special_effect': 0,

    # 自动白平衡 (AWB): 是否启用自动白平衡。True: 启用 (默认)，False: 禁用
    'awb': True,

    # AWB 增益 (AWB Gain): 是否启用自动白平衡的增益控制。True: 启用 (默认)，False: 禁用
    'awb_gain': True,

    # 白平衡模式 (WB Mode): 设置白平衡模式。可选值如下：
    # 0: 自动 (默认), 1: 阳光, 2: 多云, 3: 办公室, 4: 家庭
    'wb_mode': 0,

    # 自动曝光传感器 (AEC SENSOR): 是否启用自动曝光传感器。True: 启用 (默认)，False: 禁用
    'aec': True,

    # 自动曝光 DSP (AEC DSP): 是否启用自动曝光的数字信号处理 (DSP)。True: 启用 (默认)，False: 禁用
    'aec2': True,

    # 自动曝光等级 (AE Level): 设置自动曝光的等级。范围: -2 (最暗) 到 2 (最亮)，默认值为 0
    'ae_level': 0,

    # 曝光值 (Exposure): 设置曝光时间。范围: 0 到 1200，默认值为 204
    'aec_value': 204,

    # 自动增益控制 (AGC): 是否启用自动增益控制。True: 启用 (默认)，False: 禁用
    'agc': True,

    # 增益 (Gain): 设置摄像头增益。范围: 0 到 30，表示从 1x 到 31x 增益。默认值为 5
    'agc_gain': 30,

    # 增益上限 (Gain Ceiling): 增益上限的设置。范围: 0 (2x) 到 6 (128x)。默认值为 0
    'gainceiling': 2,

    # 黑点校正 (BPC): 是否启用黑点校正。True: 启用，False: 禁用 (默认)
    'bpc': False,

    # 白点校正 (WPC): 是否启用白点校正。True: 启用 (默认)，False: 禁用
    'wpc': True,

    # 原始伽玛校正 (Raw GMA): 是否启用原始伽玛校正。True: 启用 (默认)，False: 禁用
    'raw_gma': True,

    # 镜头校正 (Lens Correction): 是否启用镜头校正。True: 启用 (默认)，False: 禁用
    'lenc': True,

    # 水平翻转 (H-Mirror): 是否水平翻转图像。True: 启用 (默认)，False: 禁用
    'hmirror': False,

    # 垂直翻转 (V-Flip): 是否垂直翻转图像。True: 启用 (默认)，False: 禁用
    'vflip': False,

    # 缩小使能 (DCW): 是否启用下采样缩小图像。True: 启用 (默认)，False: 禁用
    'dcw': True,

    # 彩条 (Color Bar): 是否显示测试彩条。True: 显示，False: 隐藏 (默认)
    'colorbar': False,

    # 人脸检测 (Face Detection): 是否启用人脸检测。True: 启用，False: 禁用 (默认)
    'face_detect': False,

    # 人脸识别 (Face Recognition): 是否启用人脸识别。True: 启用，False: 禁用 (默认)
    'face_recognize': False
}
camera_frame_sizes = {
    10: (1600, 1200),
    9: (1280, 1024),
    8: (1024, 768),
    7: (800, 600),
    6: (640, 480),
    5: (400, 296),
    4: (320, 240),
    3: (240, 176),
    0: (160, 120)
}

# 示例：应用配置
def apply_camera_config(URL):
    if not check_connect(URL):
        print(f"无法连接到摄像头: {URL}")
        return False
    config = camera_config
    for param, value in config.items():
        configure_camera(param, value, URL)
    return True


def configure_camera(parameter, value, base_url):
    """
    配置远程摄像头的参数
    :param parameter: 配置参数名
    :param value: 配置值
    :return: None
    """
    if isinstance(value, bool):
        value = 1 if value else 0
    config_url = f"{base_url}/control?var={parameter}&val={value}"
    try:
        response = requests.get(config_url)
        if response.status_code == 200:
            pass
        else:
            print(f"配置失败: {parameter} = {value}, 状态码: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"无法连接摄像头: {e}")

def check_connect(base_url):
    try:
        requests.get(base_url, timeout=1)
        is_connected = True
    except requests.exceptions.RequestException:
        is_connected = False
    return is_connected

def get_framesize():
    frame_size = camera_frame_sizes[camera_config['framesize']]
    return frame_size
