import json

def load_config(filename='config.json'):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    except FileNotFoundError:
        raise FileNotFoundError(f"Config file not found at path: {filename}")
    
    except json.JSONDecodeError:
        raise ValueError(f"Failed to decode {filename}. Check for syntax errors.")
