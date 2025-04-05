from ultralytics import YOLO
import os
import torch

from ultralytics.nn.modules import C3
torch.serialization.add_safe_globals([C3])

def detect(file):
    model_path = os.path.join(os.path.dirname(__file__), "detect_model.pt")
    model = torch.load(model_path, weights_only=False)
    results = model(file)
    people_count = 0
    for result in results[0].boxes:
        if result.cls == 0:
            people_count += 1
    return people_count