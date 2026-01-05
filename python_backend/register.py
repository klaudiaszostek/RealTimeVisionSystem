import sys
import json
from azure.data.tables import TableServiceClient
from azure.core.exceptions import ResourceNotFoundError
from passlib.hash import pbkdf2_sha256
import config_manager

def register_user(username, password, admin_code):
    try:
        connection_string = config_manager.AZURE_STORAGE_CONNECTION_STRING
        secret_admin_code = config_manager.ADMIN_INVITE_CODE
        
        table_service = TableServiceClient.from_connection_string(connection_string)
        table_client = table_service.get_table_client(table_name="Users")

        try:
            table_client.get_entity(partition_key="users", row_key=username)
            return {"status": "error", "message": f"Username '{username}' already exists."}
        except ResourceNotFoundError:
            pass
        
        role = "user"
        if admin_code:
            if admin_code == secret_admin_code:
                role = "admin"
            else:
                return {"status": "error", "message": "Invalid Admin Code."}
        
        password_hash = pbkdf2_sha256.hash(password)
        new_user = {
            'PartitionKey': 'users',
            'RowKey': username,
            'passwordHash': password_hash,
            'role': role
        }
        table_client.create_entity(entity=new_user)
        return {"status": "success", "message": f"User '{username}' created successfully as '{role}'."}

    except Exception as e:
        return {"status": "error", "message": f"Internal error: {str(e)}"}

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(json.dumps({"status": "error", "message": "Invalid arguments. Expected username, password, and admin_code."}))
        sys.exit(1)
        
    username_arg = sys.argv[1]
    password_arg = sys.argv[2]
    admin_code_arg = sys.argv[3]
    
    final_admin_code = admin_code_arg if admin_code_arg != 'none' else None
    
    result = register_user(username_arg, password_arg, final_admin_code)
    print(json.dumps(result))
