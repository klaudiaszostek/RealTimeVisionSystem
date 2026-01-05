import sys
import os
import time
import json
import base64
import socket
import threading
import io
import warnings

import numpy as np
import cv2
import face_recognition
from azure.cognitiveservices.vision.face import FaceClient
from msrest.authentication import CognitiveServicesCredentials
from azure.storage.blob import BlobServiceClient

import config_manager
import cache_manager
from incident_recorder import IncidentRecorder
from threat_detector import ThreatDetector

warnings.filterwarnings("ignore", category=UserWarning)

IS_OFFLINE_MODE = False
LOCAL_PROFILES_CACHE = {}
SHOW_OVERLAYS = False
DETECT_WEAPONS = True
SYSTEM_STATUS = "Ready"

CLIENT_LOCK = threading.Lock()
RECONNECTION_IN_PROGRESS = False

class FacialRecognition:
    def __init__(self):
        self.known_face_encodings = []
        self.known_face_names = []
        self.encoding_cache = {}
        self.face_lock = threading.Lock()

    def load_images(self, blob_service_client, container_name):
        global IS_OFFLINE_MODE, SYSTEM_STATUS

        if blob_service_client:
            SYSTEM_STATUS = "Syncing files..."
            try:
                success = cache_manager.sync_data_from_azure()
                if not success:
                    print("Azure sync failed. Using local data.", file=sys.stderr)
            except Exception as e:
                print(f"Sync error: {e}", file=sys.stderr)

        print("Updating face database...", file=sys.stderr)
        SYSTEM_STATUS = "Processing database..."
        images_dir = cache_manager.IMAGES_DIR

        temp_encodings = []
        temp_names = []

        if not os.path.exists(images_dir):
            print("Local cache directory is empty.", file=sys.stderr)
        else:
            file_list = os.listdir(images_dir)
            valid_files = [f for f in file_list if any(f.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.webp'])]
            total_files = len(valid_files)
            calculated_count = 0

            for i, filename in enumerate(valid_files):
                name = os.path.splitext(filename)[0]

                if filename in self.encoding_cache:
                    temp_encodings.append(self.encoding_cache[filename])
                    temp_names.append(name)
                    continue

                print(f"Processing new face image {i+1}/{total_files}: {filename}", file=sys.stderr)
                path = os.path.join(images_dir, filename)

                try:
                    img = cv2.imread(path)
                    if img is None: continue

                    h, w = img.shape[:2]
                    max_dim = 500
                    if w > max_dim or h > max_dim:
                        scale = max_dim / max(w, h)
                        img = cv2.resize(img, (0, 0), fx=scale, fy=scale)

                    rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    img_encodings = face_recognition.face_encodings(rgb_img)

                    if len(img_encodings) > 0:
                        encoding = img_encodings[0]
                        temp_encodings.append(encoding)
                        temp_names.append(name)
                        self.encoding_cache[filename] = encoding
                        calculated_count += 1

                    time.sleep(0.1)

                except Exception as e:
                    print(f"Skipping file {filename}: {e}", file=sys.stderr)

            print(f"Database updated. Cached: {total_files - calculated_count}, New: {calculated_count}", file=sys.stderr)

        with self.face_lock:
            self.known_face_encodings = temp_encodings
            self.known_face_names = temp_names

        SYSTEM_STATUS = "Online" if not IS_OFFLINE_MODE else "Offline Mode"

    def identify_faces_at_locations(self, frame, face_locations):
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        clean_locations = []
        
        for loc in face_locations:
            if hasattr(loc, 'top'):
                clean_locations.append((loc.top, loc.left + loc.width, loc.top + loc.height, loc.left))
            else:
                clean_locations.append(loc)

        if not clean_locations:
            return []

        with self.face_lock:
            if len(self.known_face_encodings) == 0:
                return ["Unknown"] * len(clean_locations)

            face_encodings = face_recognition.face_encodings(rgb_frame, clean_locations)
            face_names = []

            for face_encoding in face_encodings:
                if len(self.known_face_encodings) == 0:
                    face_names.append("Unknown")
                    continue

                matches = face_recognition.compare_faces(self.known_face_encodings, face_encoding)
                name = "Unknown"
                face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)

                if len(face_distances) > 0:
                    best_match_index = np.argmin(face_distances)
                    if matches[best_match_index]:
                        name = self.known_face_names[best_match_index]
                face_names.append(name)
            
            return face_names

blob_service_client = None
face_client = None
recorder = None
fr = FacialRecognition()
threat_detector = ThreatDetector(model_filename="best.pt", conf_threshold=0.45)

def check_internet(timeout=3):
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=timeout)
        return True
    except OSError:
        return False

def create_azure_clients_safely():
    try:
        temp_blob = BlobServiceClient.from_connection_string(config_manager.AZURE_STORAGE_CONNECTION_STRING)
        credentials = CognitiveServicesCredentials(config_manager.AZURE_KEY)
        temp_face = FaceClient(config_manager.AZURE_ENDPOINT, credentials)

        temp_blob.get_account_information(timeout=3)
        return temp_blob, temp_face
    except Exception as e:
        print(f"Azure Connection Check Failed: {e}", file=sys.stderr)
        return None, None

def init_recorder_if_needed():
    global recorder
    if recorder is None:
        try:
            recorder = IncidentRecorder()
            print("Recorder initialized.", file=sys.stderr)
        except Exception as e:
            print(f"Recorder init error: {e}", file=sys.stderr)

init_recorder_if_needed()

try:
    print("Checking internet connection...", file=sys.stderr)
    if check_internet(timeout=2):
        print("Internet OK. Connecting to Azure...", file=sys.stderr)
        b_client, f_client = create_azure_clients_safely()
        if b_client and f_client:
            blob_service_client = b_client
            face_client = f_client
            print("Online Mode: Azure connected.", file=sys.stderr)
            IS_OFFLINE_MODE = False
            SYSTEM_STATUS = "Online"
        else:
            raise Exception("Azure auth failed")
    else:
        raise RuntimeError("No internet connection")
except Exception as e:
    print(f"Offline fallback triggered: {e}", file=sys.stderr)
    IS_OFFLINE_MODE = True
    SYSTEM_STATUS = "Offline Mode"

if not IS_OFFLINE_MODE:
    fr.load_images(blob_service_client, config_manager.IMAGE_CONTAINER)
else:
    fr.load_images(None, None)

LOCAL_PROFILES_CACHE = cache_manager.load_local_profiles()

def connection_monitor_loop():
    global IS_OFFLINE_MODE, RECONNECTION_IN_PROGRESS, SYSTEM_STATUS, blob_service_client, face_client

    while True:
        time.sleep(5)

        if IS_OFFLINE_MODE and not RECONNECTION_IN_PROGRESS:
            if check_internet(timeout=2):
                print("Internet restored. Attempting to reconnect...", file=sys.stderr)
                RECONNECTION_IN_PROGRESS = True
                SYSTEM_STATUS = "Reconnecting..."

                new_blob, new_face = create_azure_clients_safely()

                if new_blob and new_face:
                    with CLIENT_LOCK:
                        blob_service_client = new_blob
                        face_client = new_face

                    print("Azure client ready. Updating database in background...", file=sys.stderr)

                    try:
                        fr.load_images(blob_service_client, config_manager.IMAGE_CONTAINER)
                        print("Sync complete. Switching to ONLINE.", file=sys.stderr)
                        IS_OFFLINE_MODE = False
                        SYSTEM_STATUS = "Online"
                    except Exception as e:
                        print(f"Sync failed: {e}", file=sys.stderr)
                        IS_OFFLINE_MODE = True
                        SYSTEM_STATUS = "Offline (Sync Failed)"
                else:
                    print("Azure init failed.", file=sys.stderr)
                    SYSTEM_STATUS = "Offline (Azure Error)"

                RECONNECTION_IN_PROGRESS = False

def input_listener():
    global SHOW_OVERLAYS, DETECT_WEAPONS
    while True:
        try:
            line = sys.stdin.readline()
            if not line: break
            data = json.loads(line.strip())
            if data.get("command") == "toggle_overlays":
                SHOW_OVERLAYS = data.get("value", False)
            elif data.get("command") == "set_weapon_detection":
                DETECT_WEAPONS = data.get("value", True)
        except ValueError: pass
        except Exception: pass

def get_profile(person_name):
    if person_name == "Unknown":
        return {
            "status": "Access Denied - Unknown Person",
            "name": "",
            "surname": "Unknown",
            "dynamic_field": ""
        }
    return LOCAL_PROFILES_CACHE.get(person_name, {
        "status": f"No profile for {person_name}",
        "name": "",
        "surname": person_name,
        "dynamic_field": ""
    })

def draw_overlays(frame, faces, threats):
    for rect_dict, profil in faces:
        status = profil.get("status", "No data")
        color = (0, 0, 255)
        if "Full" in status:
            color = (0, 255, 0)
        elif "Only first floor" in status:
            color = (0, 255, 255)
            
        cv2.rectangle(frame, (rect_dict["left"], rect_dict["top"]),
                      (rect_dict["left"] + rect_dict["width"], rect_dict["top"] + rect_dict["height"]), color, 2)
    
    for threat in threats:
        x1, y1, x2, y2 = threat["box"]
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 3)
        cv2.putText(frame, threat["label"], (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

def main_loop():
    global IS_OFFLINE_MODE, SYSTEM_STATUS

    threading.Thread(target=input_listener, daemon=True).start()
    threading.Thread(target=connection_monitor_loop, daemon=True).start()

    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    if not cap.isOpened():
        raise RuntimeError("Error: Cannot open camera.")
    
    f_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    f_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    frame_counter = 0
    ASSUMED_FPS = 30.0
    FACE_INTERVAL_ONLINE = 90
    FACE_INTERVAL_OFFLINE = 15
    WEAPON_INTERVAL = 15

    last_known_faces = []
    last_known_threats = []
    last_known_theme = "theme-neutral"

    recording_end_time = 0.0
    RECORDING_EXTENSION_SECONDS = 5.0
    prev_frame_time = time.time()
    current_processing_fps = 10.0

    print("Camera started.", file=sys.stderr)

    while True:
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.01)
            continue

        current_time = time.time()
        time_diff = current_time - prev_frame_time
        prev_frame_time = current_time
        if time_diff > 0:
            current_processing_fps = (current_processing_fps * 0.9) + ((1.0/time_diff) * 0.1)

        frame_counter += 1
        current_face_interval = FACE_INTERVAL_OFFLINE if IS_OFFLINE_MODE else FACE_INTERVAL_ONLINE
        seconds_left = max(0, (current_face_interval - (frame_counter % current_face_interval)) / ASSUMED_FPS)

        check_weapon = (frame_counter % WEAPON_INTERVAL == 0) and DETECT_WEAPONS
        check_faces = (frame_counter % current_face_interval == 0)

        if check_weapon:
            scale_factor_yolo = 640.0 / frame.shape[1]
            small_frame_for_yolo = frame if scale_factor_yolo >= 1.0 else cv2.resize(frame, (0, 0), fx=scale_factor_yolo, fy=scale_factor_yolo)

            raw_threats = threat_detector.detect(small_frame_for_yolo)
            processed_threats = []
            for t in raw_threats:
                box = t["box"]
                scaled_box = [int(b / scale_factor_yolo) for b in box]
                t["label"] = f"{t['label'].upper()} {t['confidence']:.2f}"
                t["box"] = scaled_box
                processed_threats.append(t)
            last_known_threats = processed_threats
        if not DETECT_WEAPONS:
            last_known_threats = []

        if check_faces:
            analysis_frame = frame.copy()
            temp_faces_list = []
            face_locations = []

            if not IS_OFFLINE_MODE:
                if not check_internet(timeout=0.1):
                    IS_OFFLINE_MODE = True
                    SYSTEM_STATUS = "Offline (Connection Drop)"

                if not IS_OFFLINE_MODE:
                    is_success, buffer = cv2.imencode(".jpg", analysis_frame)
                    if is_success:
                        try:
                            image_stream = io.BytesIO(buffer)
                            with CLIENT_LOCK:
                                current_f_client = face_client

                            if current_f_client:
                                faces = current_f_client.face.detect_with_stream(image=image_stream, return_face_id=False, return_face_attributes=None)
                            else:
                                faces = []

                            if faces:
                                face_locations = [f.face_rectangle for f in faces]
                        except Exception as e:
                            print(f"Azure API Error: {e}", file=sys.stderr)
                            IS_OFFLINE_MODE = True
                            SYSTEM_STATUS = "Offline (Azure API Err)"

                            scale_factor = 0.5
                            rgb_small = cv2.cvtColor(cv2.resize(analysis_frame, (0, 0), fx=scale_factor, fy=scale_factor), cv2.COLOR_BGR2RGB)
                            locs = face_recognition.face_locations(rgb_small)
                            face_locations = [(int(t/scale_factor), int(r/scale_factor), int(b/scale_factor), int(l/scale_factor)) for (t, r, b, l) in locs]

            if IS_OFFLINE_MODE and not face_locations:
                scale_factor = 0.5
                small_frame = cv2.resize(analysis_frame, (0, 0), fx=scale_factor, fy=scale_factor)
                rgb_small = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
                locs_small = face_recognition.face_locations(rgb_small)
                face_locations = [(int(t/scale_factor), int(r/scale_factor), int(b/scale_factor), int(l/scale_factor)) for (t, r, b, l) in locs_small]

            if face_locations:
                face_names = fr.identify_faces_at_locations(analysis_frame, face_locations)

                for loc, name in zip(face_locations, face_names):
                    profile = get_profile(name)
                    if hasattr(loc, 'top'):
                        r_dict = {"left": loc.left, "top": loc.top, "width": loc.width, "height": loc.height}
                    else:
                        t, r, b, l = loc
                        r_dict = {"left": l, "top": t, "width": r-l, "height": b-t}
                    temp_faces_list.append((r_dict, profile))
            last_known_faces = temp_faces_list

        is_weapon_present = len(last_known_threats) > 0
        is_unknown_present = any(p["name"] == "" and p["surname"] == "Unknown" for _, p in last_known_faces)
        all_statuses = [p["status"] for _, p in last_known_faces]

        if is_weapon_present:
            last_known_theme = "theme-red"
        elif is_unknown_present:
            last_known_theme = "theme-red"
        elif any("Denied" in s or "No profile" in s for s in all_statuses):
            last_known_theme = "theme-red"
        elif any("Only first floor" in s for s in all_statuses):
            last_known_theme = "theme-yellow"
        else:
            last_known_theme = "theme-neutral"

        current_is_recording = False

        if is_weapon_present or is_unknown_present:
            recording_end_time = current_time + RECORDING_EXTENSION_SECONDS

        should_record = current_time < recording_end_time

        with CLIENT_LOCK:
            if recorder:
                if should_record and not recorder.is_recording:
                    safe_fps = max(5.0, current_processing_fps - 2.0)
                    recorder.start_recording(f_width, f_height, safe_fps)
                elif not should_record and recorder.is_recording:
                    recorder.stop_recording()

                if recorder.is_recording:
                    rec_frame = frame.copy()
                    draw_overlays(rec_frame, last_known_faces, last_known_threats)
                    recorder.write_frame(rec_frame)
                    current_is_recording = True

        data_packet = {
            "frame": None,
            "results": last_known_faces,
            "threats": last_known_threats,
            "theme": last_known_theme,
            "timer": seconds_left,
            "is_recording": current_is_recording,
            "is_offline": IS_OFFLINE_MODE,
            "weapon_detection_enabled": DETECT_WEAPONS,
            "system_status": SYSTEM_STATUS
        }

        if SHOW_OVERLAYS:
            draw_overlays(frame, last_known_faces, last_known_threats)

        ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 60])
        if ret:
            data_packet["frame"] = base64.b64encode(buffer).decode('utf-8')
            print(json.dumps(data_packet))
            sys.stdout.flush()

    cap.release()
    if recorder:
        recorder.stop_recording()

if __name__ == "__main__":
    main_loop()
