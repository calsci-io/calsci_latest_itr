UPDATE_STATE_FILE = "update_state.json"
PENDING_UPDATE_FILE = "pending_update.json"
UPDATE_STAGE_DIR = "update_stage"


def normalize_update_path(path):
    text = str(path or "").replace("\\", "/").strip()
    if text.startswith("/"):
        raise ValueError("absolute update paths are not allowed")
    parts = []
    for item in text.split("/"):
        if item in ("", "."):
            continue
        if item == "..":
            raise ValueError("parent segments are not allowed")
        parts.append(item)
    if not parts:
        raise ValueError("empty update path")
    return "/".join(parts)


def stage_relative_path(path):
    return UPDATE_STAGE_DIR + "/" + normalize_update_path(path)
