import os
import config_loader

try:
    _BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    _CONFIG_PATH = os.path.join(_BASE_DIR, '..', 'config.json')
except NameError:
    _CONFIG_PATH = '../config.json'

try:
    _config = config_loader.load_config(_CONFIG_PATH)
except Exception as e:
    raise RuntimeError(f"Failed to load config file from {_CONFIG_PATH}: {e}")

AZURE_KEY = _config.get('AZURE_KEY')
AZURE_ENDPOINT = _config.get('AZURE_ENDPOINT')
AZURE_STORAGE_CONNECTION_STRING = _config.get('AZURE_STORAGE_CONNECTION_STRING')
PROFILE_CONTAINER = _config.get('PROFILE_CONTAINER')
IMAGE_CONTAINER = _config.get('IMAGE_CONTAINER')
INCIDENT_CONTAINER = _config.get('INCIDENT_CONTAINER')
ADMIN_INVITE_CODE = _config.get('ADMIN_INVITE_CODE')

required_keys = [
    AZURE_STORAGE_CONNECTION_STRING,
    PROFILE_CONTAINER,
    IMAGE_CONTAINER,
    AZURE_KEY,
    AZURE_ENDPOINT,
    INCIDENT_CONTAINER,
    ADMIN_INVITE_CODE
]

if not all(required_keys):
    raise ValueError("One or more required keys are missing from config.json.")
