import json
import os

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), 'settings.json')
DEFAULT_SETTINGS = {
    "executables": {
        "FreeCAD_GUI": "",
        "FreeCAD_CMD": "",
        "PrePoMax": "",
        "LibreOffice_Writer": "",
        "LibreOffice_Calc": "",
        "LibreOffice_Impress": "",
    }
}


def _merge_dict(defaults, current):
    merged = defaults.copy()
    for key, value in current.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_dict(merged[key], value)
        else:
            merged[key] = value
    return merged

def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        save_settings(DEFAULT_SETTINGS)
    with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
        loaded_settings = json.load(f)

    merged_settings = _merge_dict(DEFAULT_SETTINGS, loaded_settings)
    if merged_settings != loaded_settings:
        save_settings(merged_settings)
    return merged_settings

def save_settings(settings):
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(settings, f, indent=4)
