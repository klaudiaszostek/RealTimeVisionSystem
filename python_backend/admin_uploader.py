import sys
import json
import os
import datetime
import re
from azure.storage.blob import BlobServiceClient
import config_manager

def generate_unique_id(name, surname):
    now = datetime.datetime.now()
    timestamp = now.strftime("%Y%m%d%H%M%S%f")[:-3]

    def sanitize(text):
        text = text.lower()
        text = re.sub(r'\s+', '_', text)
        text = re.sub(r'[^a-z0-9_]', '', text)
        return text

    clean_surname = sanitize(surname)
    clean_name = sanitize(name)

    if not clean_surname:
        clean_surname = "user"
        
    return f"{clean_surname}_{clean_name}_{timestamp}"

def upload_profile(user_data_json, image_path):
    try:
        blob_service_client = BlobServiceClient.from_connection_string(
            config_manager.AZURE_STORAGE_CONNECTION_STRING
        )

        user_data = json.loads(user_data_json)
        name = user_data.get('name')
        surname = user_data.get('surname')
        
        if not name or not surname:
            raise ValueError("Missing 'name' or 'surname' field in user data")
            
        user_id = generate_unique_id(name, surname)
        user_data['id'] = user_id

        json_filename = f"{user_id}.json"
        json_data_bytes = json.dumps(user_data, indent=4).encode('utf-8')

        blob_client_json = blob_service_client.get_blob_client(
            container=config_manager.PROFILE_CONTAINER,
            blob=json_filename
        )
        blob_client_json.upload_blob(json_data_bytes, overwrite=True)

        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")

        _, file_extension = os.path.splitext(image_path)
        if file_extension.lower() not in ['.jpg', '.jpeg', '.png', '.webp']:
            raise ValueError(f"Invalid image file type: {file_extension}")

        image_filename = f"{user_id}{file_extension}"

        blob_client_image = blob_service_client.get_blob_client(
            container=config_manager.IMAGE_CONTAINER,
            blob=image_filename
        )

        with open(image_path, "rb") as data:
            blob_client_image.upload_blob(data, overwrite=True)

        print(json.dumps({"status": "success", "message": f"Successfully registered ID: {user_id}"}))

    except Exception as e:
        print(json.dumps({"status": "error", "message": f"Upload error: {str(e)}"}))
        sys.exit(1)

if __name__ == "__main__":
    try:
        if len(sys.argv) != 3:
            print(json.dumps({"status": "error", "message": "Invalid arguments. Expected JSON data and image path."}))
            sys.exit(1)

        user_data_arg = sys.argv[1]
        image_path_arg = sys.argv[2]
        upload_profile(user_data_arg, image_path_arg)
    except Exception as e:
        print(json.dumps({"status": "error", "message": f"Critical error: {str(e)}"}))
        sys.exit(1)
