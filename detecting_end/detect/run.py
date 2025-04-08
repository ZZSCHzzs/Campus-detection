from ultralytics import YOLO
import os

def load_model():
    """
    预加载YOLO模型并返回
    """
    model_path = os.path.join(os.path.dirname(__file__), "detect_model.pt")
    model = YOLO(model_path)
    return model

def detect_series(image_paths, model=None):
    if model is None:
        model = load_model()
    results = {}
    
    for image_path in image_paths:
        image_results = model(image_path)
        people_count = 0
        for result in image_results[0].boxes:
            if result.cls == 0:
                people_count += 1
        results[image_path] = people_count
    
    return results

def detect(file, model=None):
    if model is None:
        model = load_model()
    results = model(file)
    people_count = 0
    for result in results[0].boxes:
        if result.cls == 0:
            people_count += 1
    return people_count

if __name__ == "__main__":
    file_path = "../test.png"  # 替换为你的图片路径
    count = detect(file_path)
    print(f"检测到人数: {count}")