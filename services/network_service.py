class NetworkService:
    def __init__(self, adapter, storage):
        self.adapter = adapter
        self.storage = storage

    def scan(self):
        return self.adapter.scan()

    def connect(self, ssid, password):
        connected = self.adapter.connect(ssid, password)
        if connected:
            self.storage.upsert_wifi_credential(ssid, password)
        return connected

    def connect_saved(self, ssid):
        for item in self.storage.get_wifi_credentials():
            if item.get("ssid") == ssid:
                return self.connect(item.get("ssid", ""), item.get("password", ""))
        return False

    def autoconnect(self):
        if not self.storage.get_setting("auto_wifi_connect", True):
            return False
        for item in self.storage.get_wifi_credentials():
            if self.connect(item.get("ssid", ""), item.get("password", "")):
                return True
        return False

    def disconnect(self):
        self.adapter.disconnect()

    def status(self):
        return self.adapter.status()

    def http_get_json(self, url):
        return self.adapter.http_get_json(url)

    def http_get_text(self, url):
        return self.adapter.http_get_text(url)

    def sync_time(self):
        return self.adapter.sync_ntp()
