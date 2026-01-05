import sys
import os
from ultralytics import YOLO

class ThreatDetector:
    def __init__(self, model_filename="best.pt", conf_threshold=0.45):
        self.conf_threshold = conf_threshold
        self.model = None
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        model_path = os.path.join(current_dir, model_filename)

        print(f"Looking for model at: {model_path}", file=sys.stderr)
        
        if not os.path.exists(model_path):
            print(f"CRITICAL ERROR: Model file not found at {model_path}", file=sys.stderr)
            print(f"Current working directory: {os.getcwd()}", file=sys.stderr)
        else:
            try:
                print("Loading YOLO model...", file=sys.stderr)
                self.model = YOLO(model_path)
                print(f"Model loaded successfully. Classes: {self.model.names}", file=sys.stderr)
            except Exception as e:
                print(f"Error loading YOLO weights: {e}", file=sys.stderr)

    def detect(self, frame):
        if self.model is None:
            return []

        detections = []
        try:
            results = self.model(frame, conf=self.conf_threshold, verbose=False)

            for r in results:
                boxes = r.boxes
                
                for box in boxes:
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    cls_id = int(box.cls[0])
                    conf = float(box.conf[0])
                    
                    if self.model.names:
                        label = self.model.names[cls_id]
                    else:
                        label = str(cls_id)

                    print(f"DETECTED: {label} ({conf:.2f})", file=sys.stderr)
                    
                    detections.append({
                        "label": label,
                        "confidence": conf,
                        "box": [int(x1), int(y1), int(x2), int(y2)]
                    })
                    
        except Exception as e:
            print(f"Inference error: {e}", file=sys.stderr)

        return detections
