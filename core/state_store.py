class StateStore:
    def __init__(self):
        self._data = {
            "ui": {},
            "system": {},
            "runtime": {},
        }

    def get(self, key, default=None):
        return self._data.get(key, default)

    def section(self, key):
        if key not in self._data or not isinstance(self._data[key], dict):
            self._data[key] = {}
        return self._data[key]

    def set(self, section, key, value):
        self.section(section)[key] = value
        return value

    def update(self, section, values):
        bucket = self.section(section)
        bucket.update(values)
        return bucket

