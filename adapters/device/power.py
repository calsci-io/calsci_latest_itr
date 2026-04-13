from adapters.device.hardware_config import BACKLIGHT_GPIO, BATTERY_ADC_PIN, BATTERY_CHARGE_PIN

try:
    import machine  # type: ignore
except ImportError:
    machine = None


BACKLIGHT_MAX_LEVEL = 15


class DevicePowerAdapter:
    def __init__(self):
        self._pwm = None
        self._pin = None
        self._adc = None
        self._charge_pin = None
        if machine is not None and BACKLIGHT_GPIO is not None:
            try:
                self._pin = machine.Pin(BACKLIGHT_GPIO, machine.Pin.OUT)
                self._pwm = machine.PWM(self._pin)
                self._pwm.freq(1000)
            except Exception:
                self._pin = None
                self._pwm = None
        if machine is not None:
            try:
                adc_pin = machine.Pin(BATTERY_ADC_PIN)
                self._adc = machine.ADC(adc_pin)
                self._adc.atten(machine.ADC.ATTN_11DB)
                self._adc.width(machine.ADC.WIDTH_12BIT)
            except Exception:
                self._adc = None
            try:
                self._charge_pin = machine.Pin(BATTERY_CHARGE_PIN, machine.Pin.IN, machine.Pin.PULL_DOWN)
            except Exception:
                self._charge_pin = None

    def set_backlight_level(self, level):
        level = max(0, min(BACKLIGHT_MAX_LEVEL, int(level)))
        duty = int((1023 * (BACKLIGHT_MAX_LEVEL - level)) / BACKLIGHT_MAX_LEVEL)
        if self._pwm is not None:
            try:
                self._pwm.duty(duty)
            except Exception:
                pass
        elif self._pin is not None:
            try:
                self._pin.value(0 if level > 0 else 1)
            except Exception:
                pass
        return level

    def battery_info(self):
        voltage = None
        charging = None
        if self._adc is not None:
            raw_value = self._adc.read()
            voltage = round((raw_value / 4095.0) * 3.3 * 2 + 0.220, 3)
        if self._charge_pin is not None:
            try:
                charging = bool(self._charge_pin.value())
            except Exception:
                charging = None
        return {
            "voltage": voltage,
            "charging": charging,
        }

    def deep_sleep(self):
        if machine is not None:
            try:
                machine.deepsleep()
            except Exception:
                pass

    def restart(self):
        if machine is not None and hasattr(machine, "reset"):
            try:
                machine.reset()
            except Exception:
                pass

    def unique_id_hex(self):
        if machine is None or not hasattr(machine, "unique_id"):
            return ""
        return "".join("{:02X}".format(byte) for byte in machine.unique_id())
