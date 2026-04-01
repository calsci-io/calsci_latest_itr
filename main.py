import _thread
import builtins
import sys

from data_modules.hardware_config import app_thread_is_enabled


def _run_app_handler():
    try:
        from process_modules.app_handler import app_handler
        app_handler()
    except Exception as exc:
        sys.print_exception(exc)


if app_thread_is_enabled() and not getattr(builtins, "_calsci_app_thread_started", False):
    builtins._calsci_app_thread_started = True
    _thread.stack_size(32 * 1024)
    _thread.start_new_thread(_run_app_handler, ())
