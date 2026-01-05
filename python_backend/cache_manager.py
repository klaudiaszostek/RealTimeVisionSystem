import os
import json
import sys
from azure.storage.blob import BlobServiceClient
import config_manager

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOCAL_DATA_DIR = os.path.join(BASE_DIR, '..', 'local_data')
IMAGES_DIR = os.path.join(LOCAL_DATA_DIR, 'images')
PROFILES_DIR = os.path.join(LOCAL_DATA_DIR, 'profiles')

def sync_data_from_azure():
    print("Starting synchronization...", file=sys.stderr)
    
    os.makedirs(IMAGES_DIR, exist_ok=True)
    os.makedirs(PROFILES_DIR, exist_ok=True)

    try:
        blob_service_client = BlobServiceClient.from_connection_string(
            config_manager.AZURE_STORAGE_CONNECTION_STRING
        )

        container_client = blob_service_client.get_container_client(config_manager.PROFILE_CONTAINER)
        for blob in container_client.list_blobs():
            local_path = os.path.join(PROFILES_DIR, blob.name)
            with open(local_path, "wb") as f:
                blob_client = container_client.get_blob_client(blob)
                data = blob_client.download_blob().readall()
                f.write(data)
        print("Profiles synced.", file=sys.stderr)

        container_client = blob_service_client.get_container_client(config_manager.IMAGE_CONTAINER)
        for blob in container_client.list_blobs():
            if not any(blob.name.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                continue
            local_path = os.path.join(IMAGES_DIR, blob.name)
            with open(local_path, "wb") as f:
                blob_client = container_client.get_blob_client(blob)
                data = blob_client.download_blob().readall()
                f.write(data)
        print("Images synced.", file=sys.stderr)
        
        return True

    except Exception as e:
        print(f"Sync warning: Could not connect to Azure. Using existing local files. Error: {e}", file=sys.stderr)
        return False

def load_local_profiles():
    profiles = {}
    if not os.path.exists(PROFILES_DIR):
        return profiles

    for filename in os.listdir(PROFILES_DIR):
        if filename.endswith(".json"):
            name = os.path.splitext(filename)[0]
            try:
                with open(os.path.join(PROFILES_DIR, filename), 'r', encoding='utf-8') as f:
                    profiles[name] = json.load(f)
            except Exception:
                pass
    return profiles
