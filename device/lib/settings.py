import json
import os

DEFAULT_BRIGHTNESS = 255
_replace = getattr(os, "replace", os.rename)


def load(path):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save(path, data):
    temp = path + ".tmp"
    with open(temp, "w") as f:
        json.dump(data, f)
    _replace(temp, path)


def get_brightness(path):
    return load(path).get("brightness", DEFAULT_BRIGHTNESS)


def set_brightness(path, value):
    data = load(path)
    data["brightness"] = value
    save(path, data)
