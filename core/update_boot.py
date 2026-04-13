import json

try:
    import os
except ImportError:
    os = None

from core.fscompat import dirname, ensure_dir, exists
from core.update_common import PENDING_UPDATE_FILE, UPDATE_STATE_FILE, stage_relative_path


def _root_join(root_dir, relative_path):
    base = str(root_dir or ".").rstrip("/")
    rel = str(relative_path or "").lstrip("/")
    if not rel:
        return base or "."
    if base in ("", "."):
        return rel
    return base + "/" + rel


def _read_json(path, default=None):
    if not exists(path):
        return default
    with open(path, "r") as handle:
        return json.load(handle)


def _write_json(path, payload):
    ensure_dir(dirname(path))
    with open(path, "w") as handle:
        json.dump(payload, handle)
    return payload


def _remove_file(path):
    if os is None or not exists(path):
        return
    try:
        os.remove(path)
    except OSError:
        pass


def apply_pending_update(root_dir):
    pending_path = _root_join(root_dir, "data/" + PENDING_UPDATE_FILE)
    state_path = _root_join(root_dir, "data/" + UPDATE_STATE_FILE)
    pending = _read_json(pending_path, None)
    if not pending:
        return False

    state = _read_json(state_path, {}) or {}
    try:
        for item in pending.get("files", []):
            relative_path = str(item or "")
            source_path = _root_join(root_dir, "data/" + stage_relative_path(relative_path))
            target_path = _root_join(root_dir, relative_path)
            with open(source_path, "r") as handle:
                payload = handle.read()
            ensure_dir(dirname(target_path))
            with open(target_path, "w") as handle:
                handle.write(payload)
        state["current_version"] = pending.get("version", state.get("current_version", ""))
        state["last_applied_version"] = pending.get("version", "")
        state["available_version"] = ""
        state["update_available"] = False
        state["status"] = "applied"
        state["last_error"] = ""
        state["pending_version"] = ""
        _write_json(state_path, state)
        _remove_file(pending_path)
        return True
    except Exception as exc:
        state["status"] = "apply_failed"
        state["last_error"] = str(exc)
        state["pending_version"] = pending.get("version", "")
        _write_json(state_path, state)
        return False
