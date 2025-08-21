import cv2
from ultralytics import YOLO

def process_stream(model, stream_url, conf_thresh=0.3, iou_thresh=0.45, window_name='Detection'):
    cap = cv2.VideoCapture(stream_url)
    if not cap.isOpened():
        print(f"[ERROR] Unable to open stream: {stream_url}")
        return

    print(f"[INFO] Processing stream: {stream_url}")
    try:
        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                print("[WARNING] Stream read failed or ended.")
                break

            try:
                results = model.predict(frame, conf=conf_thresh, iou=iou_thresh, classes=[0], verbose=False)
                annotated_frame = frame.copy()
                people_count = 0

                if results and len(results) > 0:
                    boxes = results[0].boxes
                    if boxes is not None and len(boxes) > 0:
                        for box in boxes:
                            cls_id = int(box.cls[0])
                            conf = float(box.conf[0])
                            if cls_id == 0 and conf >= conf_thresh:
                                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                                cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                                people_count += 1

                text = f'People count: {people_count}'
                cv2.putText(annotated_frame, text, (10, 50),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)
            except Exception as e:
                print(f"[WARNING] Detection failed, using original frame: {e}")
                annotated_frame = frame

            cv2.imshow(window_name, annotated_frame)
            key = cv2.waitKey(1) & 0xFF
            if key in (ord('q'), 27):
                print("[INFO] Exit requested by user.")
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()
        print("[DONE] Stream processing stopped.")

if __name__ == '__main__':
    model_path = 'detect_model.pt'
    stream_url = 'http://192.168.1.101:81/stream'

    model = YOLO(model_path)
    process_stream(model, stream_url)