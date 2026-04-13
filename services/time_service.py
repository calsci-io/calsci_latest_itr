try:
    import time as _time_mod
except ImportError:
    import utime as _time_mod  # type: ignore


class TimeService:
    def __init__(self, network_service):
        self.network = network_service

    def indian_time(self):
        status = self.network.status()
        if not status.get("connected"):
            raise RuntimeError("WiFi not connected")
        if not self.network.sync_time():
            raise RuntimeError("NTP sync unavailable")

        current = _time_mod.localtime()
        if hasattr(_time_mod, "mktime"):
            epoch = int(_time_mod.mktime(current)) + 19800
            current = _time_mod.localtime(epoch)

        year, month, day, hour, minute, second = current[:6]
        if hour == 0:
            hour_12 = 12
            period = "AM"
        elif hour < 12:
            hour_12 = hour
            period = "AM"
        elif hour == 12:
            hour_12 = 12
            period = "PM"
        else:
            hour_12 = hour - 12
            period = "PM"
        return {
            "date": "%02d/%02d/%04d" % (day, month, year),
            "time": "%02d:%02d:%02d %s" % (hour_12, minute, second, period),
        }
