import gc
import machine
import st7565 as display
from data_modules.hardware_config import (
    app_thread_is_enabled,
    backlight_is_enabled,
    deepsleep_hold_pin,
    display_is_enabled,
    display_pins,
)
from sleeping_features import keypad_normal

# ----------------------------
# Hardware bootstrap
# ----------------------------
DISPLAY_PINS = display_pins()
DEEPSLEEP_KEY_PIN = deepsleep_hold_pin()

keypad_normal()
if DEEPSLEEP_KEY_PIN is not None:
    try:
        machine.Pin(DEEPSLEEP_KEY_PIN, machine.Pin.OUT, value=1, hold=False)
    except Exception:
        pass

if display_is_enabled():
    try:
        display.init(*DISPLAY_PINS)
        display.clear_display()
    except Exception:
        pass

gc.enable()
print("free ram initially=", gc.mem_free())
print("ram allocated initially=", gc.mem_alloc())


# ----------------------------
# Runtime globals
# ----------------------------
import builtins
import calsci_runtime
from data_modules.object_handler import data_bucket, display as active_display, menu, form, nav, text, typer

if backlight_is_enabled():
    try:
        from apps.settings.backlight import apply_saved_backlight
        apply_saved_backlight()
    except Exception:
        pass

builtins.display = active_display
builtins.typer = typer
builtins.set_calsci_keypad_blocked = calsci_runtime.set_calsci_keypad_blocked
builtins.block_calsci_keypad = calsci_runtime.block_calsci_keypad
builtins.unblock_calsci_keypad = calsci_runtime.unblock_calsci_keypad
builtins.calsci_keypad_blocked = calsci_runtime.calsci_keypad_blocked
builtins.calsci_app_thread_enabled = app_thread_is_enabled()

# WiFi startup stays disabled for fast boot.
builtins.sta_if = None
data_bucket["connection_status_g"] = False
data_bucket["ssid_g"] = ""


# ----------------------------
# Hybrid REPL helpers
# ----------------------------
try:
    import calsci_hybrid
except ImportError:
    calsci_hybrid = None
except Exception as _hyb_import_exc:
    calsci_hybrid = None
    print("HYBRID_IMPORT_ERR:", _hyb_import_exc)
    try:
        import sys as _sys
        _sys.print_exception(_hyb_import_exc)
    except Exception:
        pass

if calsci_hybrid is not None:
    try:
        calsci_hybrid.install(
            data_bucket=data_bucket,
            typer=typer,
            menu=menu,
            form=form,
            text=text,
            nav=nav,
            runtime=calsci_runtime,
            namespace=globals(),
        )
    except Exception as _hyb_exc:
        print("HYBRID_BRIDGE_ERR:", _hyb_exc)
        try:
            import sys as _sys
            _sys.print_exception(_hyb_exc)
        except Exception:
            pass
