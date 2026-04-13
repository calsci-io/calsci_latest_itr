class MenuScreen:
    screen_type = "menu"

    def __init__(self, title, items, selected=0, footer="", subtitle=""):
        self.title = title
        self.items = list(items)
        self.selected = int(selected)
        self.footer = footer
        self.subtitle = subtitle


class TextScreen:
    screen_type = "text"

    def __init__(self, title, lines, footer="", scroll=0):
        self.title = title
        self.lines = list(lines)
        self.footer = footer
        self.scroll = int(scroll)


class FormField:
    def __init__(self, key, label, value=""):
        self.key = key
        self.label = label
        self.value = value


class FormScreen:
    screen_type = "form"

    def __init__(self, title, fields, selected=0, footer="", message=""):
        self.title = title
        self.fields = list(fields)
        self.selected = int(selected)
        self.footer = footer
        self.message = message


class CanvasScreen:
    screen_type = "canvas"

    def __init__(self, title, buffer_bytes, footer="", meta=None):
        self.title = title
        self.buffer_bytes = buffer_bytes
        self.footer = footer
        self.meta = meta or {}

