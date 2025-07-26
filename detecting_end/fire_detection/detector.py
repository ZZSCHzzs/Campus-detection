import cv2
import numpy as np
from pathlib import Path
from typing import Tuple


class FireDetector:
    """可插拔的火灾检测模块"""

    def __init__(self, model_path: str = None, threshold: float = 0.7):
        """
        Args:
            model_path: 可选自定义模型路径
            threshold: 检测阈值(0-1)
        """
        self.threshold = threshold
        self.model = self._load_model(
            model_path or Path(__file__).parent / "models" / "default.onnx"
        )

    def _load_model(self, model_path: Path) -> cv2.dnn_Net:
        """加载ONNX模型"""
        if not model_path.exists():
            raise FileNotFoundError(f"Model not found at {model_path}")
        net = cv2.dnn.readNetFromONNX(str(model_path))
        net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
        net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
        return net

    def detect(self, frame: np.ndarray) -> Tuple[bool, float]:
        """
        执行火灾检测

        Args:
            frame: BGR格式的numpy数组(H,W,3)

        Returns:
            tuple: (是否检测到火灾, 置信度)
        """
        blob = cv2.dnn.blobFromImage(
            frame,
            scalefactor=1 / 255.0,
            size=(64, 64),
            mean=(0.5, 0.5, 0.5),
            swapRB=True
        )
        self.model.setInput(blob)
        pred = self.model.forward()
        confidence = float(pred[0][0])
        return confidence > self.threshold, confidence