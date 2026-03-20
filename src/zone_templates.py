import json
import os
from typing import Any, Dict

TEMPLATES_FILE = "data/zone_templates.json"

def _ensure_dir():
    if not os.path.exists("data"):
        os.makedirs("data")
    if not os.path.exists(TEMPLATES_FILE):
        with open(TEMPLATES_FILE, "w") as f:
            json.dump({}, f)

def save_template(name, canvas_json, display_names):
    _ensure_dir()
    data: Dict[str, Any] = {}
    with open(TEMPLATES_FILE, "r") as f:
        try:
            raw = json.load(f)
            if isinstance(raw, dict):
                data.update(raw)
        except Exception:
            pass
    
    data[name] = {
        "canvas": canvas_json,
        "names": display_names
    }
    
    with open(TEMPLATES_FILE, "w") as f:
        json.dump(data, f, indent=2)

def load_template(name):
    _ensure_dir()
    with open(TEMPLATES_FILE, "r") as f:
        data = json.load(f)
    return data.get(name)

def list_templates():
    _ensure_dir()
    with open(TEMPLATES_FILE, "r") as f:
        try:
            data = json.load(f)
            return list(data.keys())
        except:
            return []

def delete_template(name):
    _ensure_dir()
    with open(TEMPLATES_FILE, "r") as f:
        data = json.load(f)
    
    if name in data:
        del data[name]
        with open(TEMPLATES_FILE, "w") as f:
            json.dump(data, f, indent=2)
        return True
    return False
