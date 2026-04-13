import json
import os

from core.fscompat import dirname, ensure_dir, exists, is_dir


class DeviceStorageAdapter:
    def __init__(self, root_dir, config):
        self.root_dir = root_dir
        self.data_dir = root_dir + "/" + config.get("data_dir", "data")

    def ensure_dir(self, path):
        ensure_dir(path)

    def ensure_data_dirs(self):
        self.ensure_dir(self.data_dir)

    def path(self, name):
        return self.data_dir + "/" + name

    def root_path(self, name=""):
        text = str(name or "").lstrip("/")
        if not text:
            return self.root_dir
        return self.root_dir + "/" + text

    def exists(self, name):
        return exists(self.path(name))

    def exists_path(self, path):
        return exists(path)

    def read_json(self, name, default=None):
        path = self.path(name)
        if not exists(path):
            return default
        with open(path, "r") as handle:
            return json.load(handle)

    def write_json(self, name, payload):
        with open(self.path(name), "w") as handle:
            json.dump(payload, handle)
        return payload

    def read_json_path(self, path, default=None):
        if not exists(path):
            return default
        with open(path, "r") as handle:
            return json.load(handle)

    def write_json_path(self, path, payload):
        ensure_dir(dirname(path))
        with open(path, "w") as handle:
            json.dump(payload, handle)
        return payload

    def read_text_path(self, path, default=None):
        if not exists(path):
            return default
        with open(path, "r") as handle:
            return handle.read()

    def write_text_path(self, path, text):
        ensure_dir(dirname(path))
        with open(path, "w") as handle:
            handle.write(text)
        return text

    def remove_path(self, path):
        if not exists(path):
            return False
        try:
            os.remove(path)
            return True
        except OSError:
            return False

    def remove_tree_path(self, path):
        if not exists(path):
            return False
        if not is_dir(path):
            return self.remove_path(path)
        for name in os.listdir(path):
            child = path.rstrip("/") + "/" + name
            if is_dir(child):
                self.remove_tree_path(child)
            else:
                self.remove_path(child)
        try:
            os.rmdir(path)
        except OSError:
            return False
        return True
