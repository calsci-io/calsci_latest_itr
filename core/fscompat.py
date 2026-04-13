import os


def dirname(path):
    text = str(path or "")
    if text == "":
        return ""
    if text != "/":
        text = text.rstrip("/")
    if text == "":
        return "/"
    marker = text.rfind("/")
    if marker < 0:
        return ""
    if marker == 0:
        return "/"
    return text[:marker]


def root_dir_from_file(file_path, levels=1):
    current = str(file_path or "")
    for _ in range(int(levels)):
        current = dirname(current)
    return current or "."


def exists(path):
    try:
        os.stat(path)
        return True
    except OSError:
        return False


def is_dir(path):
    try:
        os.listdir(path)
        return True
    except OSError:
        return False


def ensure_dir(path):
    if is_dir(path):
        return
    parent = dirname(path)
    if parent not in ("", "/", path) and not is_dir(parent):
        ensure_dir(parent)
    try:
        os.mkdir(path)
    except OSError:
        if not is_dir(path):
            raise
