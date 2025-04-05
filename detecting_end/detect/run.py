from ultralytics import YOLO
import os
import torch
from torch.serialization import add_safe_globals
from ultralytics.nn.tasks import DetectionModel

# 将 DetectionModel 添加到安全全局对象中
add_safe_globals([DetectionModel])

def detect(file):
    model_path = os.path.join(os.path.dirname(__file__), "detect_model.pt")
    model = YOLO(model_path)
    results = model(file)
    people_count = 0
    for result in results[0].boxes:
        if result.cls == 0:
            people_count += 1
    return people_count