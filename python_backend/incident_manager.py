import sys
import json
import datetime
import os
from azure.data.tables import TableClient
from azure.storage.blob import generate_blob_sas, BlobSasPermissions, BlobServiceClient
import config_manager

def extract_account_credentials(connection_string):
    try:
        items = connection_string.split(';')
        account_name = None
        account_key = None
        for item in items:
            if item.startswith('AccountName='):
                account_name = item.replace('AccountName=', '')
            elif item.startswith('AccountKey='):
                account_key = item.replace('AccountKey=', '')
        return account_name, account_key
    except Exception:
        return None, None

def extract_timestamp_from_filename(filename):
    try:
        name_without_ext = os.path.splitext(filename)[0]
        date_part = name_without_ext.replace("incident_", "")
        dt = datetime.datetime.strptime(date_part, "%Y%m%d_%H%M%S")
        return dt.isoformat()
    except Exception:
        return None

def list_incidents():
    try:
        table_client = TableClient.from_connection_string(
            config_manager.AZURE_STORAGE_CONNECTION_STRING, 
            table_name="Incidents"
        )
        account_name, account_key = extract_account_credentials(config_manager.AZURE_STORAGE_CONNECTION_STRING)
        
        entities = table_client.list_entities()
        results = []
        
        for entity in entities:
            row_key = entity['RowKey']
            timestamp_str = extract_timestamp_from_filename(row_key)
            if not timestamp_str:
                timestamp_str = entity.get('Timestamp', datetime.datetime.now()).isoformat()
            
            video_url_with_sas = ""
            if account_name and account_key:
                try:
                    sas_token = generate_blob_sas(
                        account_name=account_name,
                        container_name=config_manager.INCIDENT_CONTAINER,
                        blob_name=row_key,
                        account_key=account_key,
                        permission=BlobSasPermissions(read=True),
                        expiry=datetime.datetime.utcnow() + datetime.timedelta(hours=1)
                    )
                    base_url = f"https://{account_name}.blob.core.windows.net/{config_manager.INCIDENT_CONTAINER}/{row_key}"
                    video_url_with_sas = f"{base_url}?{sas_token}"
                except Exception:
                    video_url_with_sas = entity.get('VideoUrl', '')
            
            results.append({
                "id": row_key,
                "status": entity.get('Status', 'New'),
                "timestamp": timestamp_str,
                "videoUrl": video_url_with_sas
            })
            
        results.sort(key=lambda x: x['timestamp'], reverse=True)
        return {"status": "success", "data": results}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def update_incident_status(row_key, new_status):
    try:
        table_client = TableClient.from_connection_string(
            config_manager.AZURE_STORAGE_CONNECTION_STRING, 
            table_name="Incidents"
        )
        entity = table_client.get_entity(partition_key="incidents", row_key=row_key)
        entity["Status"] = new_status
        table_client.update_entity(mode="merge", entity=entity)
        return {"status": "success", "message": f"Updated to {new_status}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def delete_incident(row_key):
    try:
        table_client = TableClient.from_connection_string(
            config_manager.AZURE_STORAGE_CONNECTION_STRING, 
            table_name="Incidents"
        )
        table_client.delete_entity(partition_key="incidents", row_key=row_key)
        
        blob_service = BlobServiceClient.from_connection_string(config_manager.AZURE_STORAGE_CONNECTION_STRING)
        blob_client = blob_service.get_blob_client(container=config_manager.INCIDENT_CONTAINER, blob=row_key)
        
        if blob_client.exists():
            blob_client.delete_blob()
            
        return {"status": "success", "message": f"Deleted incident {row_key}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "list"
    
    if command == "list":
        print(json.dumps(list_incidents()))
    elif command == "update":
        if len(sys.argv) != 4:
            print(json.dumps({"status": "error", "message": "Missing arguments"}))
        else:
            print(json.dumps(update_incident_status(sys.argv[2], sys.argv[3])))
    elif command == "delete":
        if len(sys.argv) != 3:
             print(json.dumps({"status": "error", "message": "Missing ID"}))
        else:
             print(json.dumps(delete_incident(sys.argv[2])))
