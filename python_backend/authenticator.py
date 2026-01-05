import sys
import json
import os
from azure.data.tables import TableServiceClient
from azure.core.exceptions import ResourceNotFoundError
from passlib.hash import pbkdf2_sha256
import config_manager

CACHE_DIR = os.path.join(os.path.dirname(__file__), '..', 'local_data')
USERS_CACHE_FILE = os.path.join(CACHE_DIR, 'users_cache.json')

def save_user_to_cache(username, password_hash, role):
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        cache = {}
        if os.path.exists(USERS_CACHE_FILE):
            try:
                with open(USERS_CACHE_FILE, 'r', encoding='utf-8') as f:
                    cache = json.load(f)
            except Exception:
                cache = {}
        
        cache[username] = {"passwordHash": password_hash, "role": role}
        
        with open(USERS_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, indent=4)
    except Exception:
        pass

def authenticate_offline(username, password):
    if not os.path.exists(USERS_CACHE_FILE):
        return {"status": "error", "message": "Offline login unavailable (cache empty)."}
    
    try:
        with open(USERS_CACHE_FILE, 'r', encoding='utf-8') as f:
            cache = json.load(f)
        
        user_data = cache.get(username)
        if not user_data:
            return {"status": "error", "message": "User not found in offline cache."}
        
        stored_hash = user_data.get("passwordHash")
        if pbkdf2_sha256.verify(password, stored_hash):
            return {
                "status": "success",
                "username": username,
                "role": user_data.get("role", "user"),
                "mode": "offline"
            }
        else:
            return {"status": "error", "message": "Invalid password."}
            
    except Exception as e:
        return {"status": "error", "message": f"Offline auth error: {str(e)}"}

def authenticate(username, password):
    try:
        connection_string = config_manager.AZURE_STORAGE_CONNECTION_STRING
        table_service = TableServiceClient.from_connection_string(connection_string)
        table_client = table_service.get_table_client(table_name="Users")

        try:
            user_entity = table_client.get_entity(partition_key="users", row_key=username)
        except ResourceNotFoundError:
            return {"status": "error", "message": "Invalid username or password."}

        stored_hash = user_entity.get("passwordHash")
        role = user_entity.get("role", "user")

        if stored_hash and pbkdf2_sha256.verify(password, stored_hash):
            save_user_to_cache(username, stored_hash, role)
            return {
                "status": "success",
                "username": user_entity['RowKey'],
                "role": role,
                "mode": "online"
            }
        else:
            return {"status": "error", "message": "Invalid username or password."}

    except Exception:
        return authenticate_offline(username, password)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(json.dumps({"status": "error", "message": "Invalid arguments."}))
        sys.exit(1)
        
    username_arg = sys.argv[1]
    password_arg = sys.argv[2]
    
    result = authenticate(username_arg, password_arg)
    print(json.dumps(result))
