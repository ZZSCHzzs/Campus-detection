from ultralytics import YOLO
import os


def detect(file):
    model_path = os.path.join(os.path.dirname(__file__), "detect_model.pt")
    model = YOLO(model_path)
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