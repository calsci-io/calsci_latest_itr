try:
    import network  # type: ignore
except ImportError:
    network = None

try:
    import urequests as requests  # type: ignore
except Exception:
    try:
        import requests  # type: ignore
    except Exception:
        requests = None

try:
    import ujson as json  # type: ignore
except Exception:
    import json

try:
    import ntptime  # type: ignore
except Exception:
    ntptime = None

try:
    import utime as _time_mod
except ImportError:
    import time as _time_mod


def _sleep_ms(ms):
    if hasattr(_time_mod, "sleep_ms"):
        _time_mod.sleep_ms(ms)
    else:
        _time_mod.sleep(ms / 1000.0)


class DeviceNetworkAdapter:
    def __init__(self):
        self._sta = network.WLAN(network.STA_IF) if network is not None else None
        if self._sta is not None:
            try:
                self._sta.active(True)
            except Exception:
                pass

    def scan(self):
        if self._sta is None:
            return []
        items = []
        for network_info in self._sta.scan():
            try:
                items.append(network_info[0].decode())
            except Exception:
                items.append(str(network_info[0]))
        return items

    def connect(self, ssid, password, timeout_ms=10000):
        if self._sta is None:
            return False
        self._sta.active(True)
        if self._sta.isconnected():
            return True
        self._sta.connect(ssid, password)
        waited = 0
        while waited < timeout_ms:
            if self._sta.isconnected():
                return True
            _sleep_ms(100)
            waited += 100
        return self._sta.isconnected()

    def disconnect(self, timeout_ms=2000):
        if self._sta is None:
            return False
        try:
            self._sta.disconnect()
        except Exception:
            return False
        waited = 0
        while waited < timeout_ms:
            if not self._sta.isconnected():
                return True
            _sleep_ms(100)
            waited += 100
        try:
            self._sta.active(False)
            _sleep_ms(100)
            self._sta.active(True)
        except Exception:
            pass
        return not self._sta.isconnected()

    def status(self):
        if self._sta is None:
            return {"connected": False, "ssid": "", "ifconfig": ()}
        connected = bool(self._sta.isconnected())
        if not connected:
            return {"connected": False, "ssid": "", "ifconfig": ()}
        ssid = ""
        try:
            ssid = self._sta.config("essid") or ""
        except Exception:
            pass
        return {
            "connected": connected,
            "ssid": ssid,
            "ifconfig": tuple(self._sta.ifconfig()),
        }

    def _http_get(self, url):
        if requests is None:
            raise RuntimeError("requests unavailable")
        response = None
        try:
            try:
                response = requests.get(url, timeout=10)
            except TypeError:
                response = requests.get(url)
            status_code = getattr(response, "status_code", 200)
            if status_code != 200:
                raise RuntimeError("HTTP %s" % status_code)
            text = getattr(response, "text", "")
            if isinstance(text, bytes):
                text = text.decode("utf-8")
            return text
        finally:
            if response is not None:
                try:
                    response.close()
                except Exception:
                    pass

    def http_get_json(self, url):
        text = self._http_get(url)
        return json.loads(text)

    def http_get_text(self, url):
        return self._http_get(url)

    def sync_ntp(self):
        if ntptime is None:
            return False
        ntptime.settime()
        return True
