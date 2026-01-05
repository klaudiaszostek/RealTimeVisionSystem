import sys
import os
import json
import io
import numpy as np
import cv2
import face_recognition
from azure.storage.blob import BlobServiceClient
from azure.cognitiveservices.vision.face import FaceClient
from msrest.authentication import CognitiveServicesCredentials

import config_loader

class FacialRecognition:
    def __init__(self):
        self.known_face_encodings = []
        self.known_face_names = []

    def load_encoding_images_from_azure(self, blob_service_client, container_name):
        print(f"Loading images from Azure container '{container_name}'...", file=sys.stderr)
        
        try:
            container_client = blob_service_client.get_container_client(container_name)
            blob_list = container_client.list_blobs()
            
            image_count = 0
            for blob in blob_list:
                print(f"Processing image: {blob.name}", file=sys.stderr)
                
                base_name = os.path.basename(blob.name)
                filename, ext = os.path.splitext(base_name)
                
                if ext.lower() not in ['.jpg', '.jpeg', '.png', '.webp']:
                    print(f"Skipping (invalid format): {blob.name}", file=sys.stderr)
                    continue

                blob_client = container_client.get_blob_client(blob)
                downloader = blob_client.download_blob()
                image_data_stream = downloader.readall()
                
                image_data_np = np.frombuffer(image_data_stream, np.uint8)
                img = cv2.imdecode(image_data_np, cv2.IMREAD_COLOR)

                if img is None:
                    print(f"Failed to decode image {blob.name}, skipping...", file=sys.stderr)
                    continue
                    
                rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

                img_encodings = face_recognition.face_encodings(rgb_img)
                if len(img_encodings) == 0:
                    print(f"No face found in {blob.name}, skipping...", file=sys.stderr)
                    continue

                img_encoding = img_encodings[0]
                self.known_face_encodings.append(img_encoding)
                self.known_face_names.append(filename)
                print(f"Encoded: {filename}", file=sys.stderr)
                image_count += 1

            print(f"Successfully loaded {image_count} face images from Azure.", file=sys.stderr)

        except Exception as e:
            print(f"CRITICAL ERROR loading images: {e}", file=sys.stderr)
            sys.exit(1)

    def identify_faces_at_locations(self, frame, azure_face_rectangles):
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        locations_as_tuples = []
        for rect in azure_face_rectangles:
            y1 = rect.top
            x1 = rect.left
            y2 = y1 + rect.height
            x2 = x1 + rect.width
            locations_as_tuples.append((y1, x2, y2, x1))
            
        face_encodings = face_recognition.face_encodings(rgb_frame, locations_as_tuples)
        face_names = []
        
        for face_encoding in face_encodings:
            matches = face_recognition.compare_faces(self.known_face_encodings, face_encoding)
            name = "Unknown"

            face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
            if len(face_distances) > 0:
                best_match_index = np.argmin(face_distances)
                if matches[best_match_index]:
                    name = self.known_face_names[best_match_index]
            face_names.append(name)
            
        return face_names

config_path = os.path.join(os.path.dirname(__file__), '..', 'config.json')
config = config_loader.load_config(config_path)

try:
    AZURE_KEY = config['AZURE_KEY']
    AZURE_ENDPOINT = config['AZURE_ENDPOINT']
    AZURE_STORAGE_CONNECTION_STRING = config['AZURE_STORAGE_CONNECTION_STRING']   
    PROFILE_CONTAINER = config['PROFILE_CONTAINER']
    IMAGE_CONTAINER = config['IMAGE_CONTAINER']
except KeyError as e:
    print(f"FATAL ERROR: Missing config key: {e}", file=sys.stderr)
    sys.exit(1)

try:
    blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
    print("Connected to Azure Blob Storage.", file=sys.stderr)
except Exception as e:
    print(f"Storage connection error: {e}", file=sys.stderr)
    sys.exit(1)

try:
    credentials = CognitiveServicesCredentials(AZURE_KEY)
    face_client = FaceClient(AZURE_ENDPOINT, credentials)
    print("Authenticated with Azure Face API.", file=sys.stderr)
except Exception as e:
    print(f"Face API authentication error: {e}", file=sys.stderr)
    sys.exit(1)

fr = FacialRecognition()
fr.load_encoding_images_from_azure(blob_service_client, IMAGE_CONTAINER)

def download_profile_data(person_name):
    if person_name == "Unknown":
        return {
            "status": "Access Denied - Unknown Person",
            "name": "",
            "surname": "Unknown",
            "dynamic_field": ""
        }
        
    file_name = f"{person_name}.json"
    
    try:
        blob_client = blob_service_client.get_blob_client(container=PROFILE_CONTAINER, blob=file_name)
        downloader = blob_client.download_blob()
        blob_data = downloader.readall()
        profil = json.loads(blob_data.decode('utf-8'))
        return profil
        
    except Exception:
        print(f"No profile found for '{file_name}'.", file=sys.stderr)
        return {
            "status": f"No profile for {person_name}",
            "name": "",
            "surname": person_name,
            "dynamic_field": ""
        }

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Error: Cannot open camera.", file=sys.stderr)
    sys.exit(1)

frame_counter = 0
PROCESS_EVERY_N_FRAMES = 120
ASSUMED_FPS = 30.0
last_known_results = []

print("Camera started. Press 'ESC' to exit.", file=sys.stderr)

while True:
    ret, frame = cap.read()
    if not ret:
        print("Frame reading error.", file=sys.stderr)
        break

    frame_counter += 1

    if frame_counter % PROCESS_EVERY_N_FRAMES == 0:
        try:
            is_success, buffer = cv2.imencode(".jpg", frame)
            if not is_success:
                print("Frame conversion error.", file=sys.stderr)
                continue
            
            image_stream = io.BytesIO(buffer)

            detected_faces_azure = face_client.face.detect_with_stream(
                image=image_stream,
                return_face_id=False,
                return_face_attributes=None
            )
            
            temp_results_list = []
            
            if detected_faces_azure:
                print(f"Azure detected {len(detected_faces_azure)} faces. Identifying...", file=sys.stderr)
                
                azure_rectangles = [face.face_rectangle for face in detected_faces_azure]
                face_names = fr.identify_faces_at_locations(frame, azure_rectangles)

                print("Faces recognized. Downloading profiles...", file=sys.stderr)
                
                for rect, name in zip(azure_rectangles, face_names):
                    data_profile = download_profile_data(name)
                    temp_results_list.append((rect, data_profile))
            
            last_known_results = temp_results_list

        except Exception as e:
            print(f"API/Identification error: {e}", file=sys.stderr)
            last_known_results = []

    frames_left = PROCESS_EVERY_N_FRAMES - (frame_counter % PROCESS_EVERY_N_FRAMES)
    seconds_left = frames_left / ASSUMED_FPS
    timer_text = f"Next analysis in: {seconds_left:.1f} s"
    cv2.putText(frame, timer_text, (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

    if last_known_results:
        for rect, profil in last_known_results:
            x1 = rect.left
            y1 = rect.top
            x2 = rect.left + rect.width
            y2 = rect.top + rect.height
            
            status = profil.get("status", "No data available")
            color = (0, 0, 255)
            
            if "All" in status:
                color = (0, 255, 0)
            elif "Only first floor" in status:
                color = (0, 255, 255)

            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

            name = profil.get("name", "")
            surname = profil.get("surname", "Unknown")
            dynamic_field = profil.get("dynamic_field", "")

            cv2.putText(frame, f"{name} {surname}", (x1, y1 - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            cv2.putText(frame, f"Apartment: {dynamic_field}", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
            cv2.putText(frame, f"Status: {status}", (x1, y2 + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

    cv2.imshow("Facial Analysis", frame)

    key = cv2.waitKey(1)
    if key == 27:
        break

cap.release()
cv2.destroyAllWindows()
print("Finished.", file=sys.stderr)
