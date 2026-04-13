BACKLIGHT_MAX_LEVEL = 15


class PowerService:
    def __init__(self, adapter, storage):
        self.adapter = adapter
        self.storage = storage
        level = self.storage.get_setting("backlight_level", BACKLIGHT_MAX_LEVEL)
        self.adapter.set_backlight_level(level if self.storage.get_setting("backlight", True) else 0)

    def set_backlight_level(self, level):
        level = self.adapter.set_backlight_level(level)
        self.storage.set_setting("backlight_level", level)
        self.storage.set_setting("backlight", level > 0)
        return level

    def get_backlight_level(self):
        return int(self.storage.get_setting("backlight_level", BACKLIGHT_MAX_LEVEL))

    def battery_info(self):
        return self.adapter.battery_info()

    def deep_sleep(self):
        self.adapter.deep_sleep()

    def restart(self):
        if hasattr(self.adapter, "restart"):
            self.adapter.restart()

    def unique_id_hex(self):
        return self.adapter.unique_id_hex()
