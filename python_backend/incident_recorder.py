import cv2
import os
import sys
import datetime
import threading
import time
import tempfile
from azure.storage.blob import BlobServiceClient
from azure.data.tables import TableClient
import config_manager

class IncidentRecorder:
    def __init__(self):
        self.is_recording = False
        self.video_writer = None
        self.current_file_path = None
        self.blob_service_client = None
        
        try:
            self.blob_service_client = BlobServiceClient.from_connection_string(
                config_manager.AZURE_STORAGE_CONNECTION_STRING
            )
        except Exception as e:
            print(f"Azure connection error: {e}", file=sys.stderr)

    def start_recording(self, frame_width, frame_height, fps=20.0):
        if self.is_recording:
            return

        self.is_recording = True
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"incident_{timestamp}.webm"
        self.current_file_path = os.path.join(tempfile.gettempdir(), filename)
        
        fourcc = cv2.VideoWriter_fourcc(*'vp80')
        
        self.video_writer = cv2.VideoWriter(
            self.current_file_path, fourcc, fps, (frame_width, frame_height)
        )
        print(f"Started recording: {filename}", file=sys.stderr)

    def write_frame(self, frame):
        if self.is_recording and self.video_writer:
            self.video_writer.write(frame)

    def stop_recording(self):
        if not self.is_recording:
            return

        self.is_recording = False
        if self.video_writer:
            self.video_writer.release()
            self.video_writer = None
            print("Stopped recording.", file=sys.stderr)
            
            if self.current_file_path:
                upload_thread = threading.Thread(
                    target=self._upload_worker,
                    args=(self.current_file_path, os.path.basename(self.current_file_path))
                )
                upload_thread.start()
                self.current_file_path = None

    def _upload_worker(self, local_path, cloud_filename):
        time.sleep(1.5) 
        
        try:
            print(f"Starting upload for {cloud_filename}...", file=sys.stderr)
            
            blob_client = self.blob_service_client.get_blob_client(
                container=config_manager.INCIDENT_CONTAINER,
                blob=cloud_filename
            )
            
            with open(local_path, "rb") as data:
                blob_client.upload_blob(data, overwrite=True)
            
            print("Blob uploaded successfully. Updating Table...", file=sys.stderr)

            table_service = TableClient.from_connection_string(
                conn_str=config_manager.AZURE_STORAGE_CONNECTION_STRING,
                table_name="Incidents"
            )
            
            incident_entity = {
                "PartitionKey": "incidents",
                "RowKey": cloud_filename,
                "Timestamp": datetime.datetime.utcnow(),
                "Status": "New",
                "VideoUrl": blob_client.url
            }
            
            table_service.create_entity(entity=incident_entity)
            
            print(f"SUCCESS: {cloud_filename} registered in DB.", file=sys.stderr)

        except Exception as e:
            print(f"CRITICAL ERROR during upload: {str(e)}", file=sys.stderr)
            
        finally:
            if os.path.exists(local_path):
                try:
                    os.remove(local_path)
                except:
                    pass
