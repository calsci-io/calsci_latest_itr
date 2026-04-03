import st7565 as display

try:
    import tools

    if hasattr(display, "graphics") and not hasattr(display.graphics, "pixels_changed"):
        display.graphics = tools.refresh(display.graphics, pixels_changed=200)
except Exception:
    pass

from data_modules.object_handler import (
    app,
    current_app,
    form,
    form_refresh,
    keypad_state_manager,
    keypad_state_manager_reset,
    nav,
    typer,
)


APP_NAME = "table_buffer_demo"
APP_GROUP = "installed_apps"

_HEADERS = ["X", "Y1", "Y1'", "Y2", "Y2'", "LONG", "NOTE", "TAG"]
_VALUES = [
    ["1", "2", "2.125", "4", "4.500", "123456789ABCDE", "first row scroll test", "A1"],
    ["2", "3.75", "3.125", "8", "8.875", "ABCDEFG123456789", "second row long note", "B2"],
    ["3", "-7.5", "-6.25", "16", "15.500", "value-overflow-0003", "third row sample text", "C3"],
    ["4", "12.25", "10.75", "32", "31.250", "scroll-check-0004", "fourth row wider data", "D4"],
    ["5", "18.5", "17.0", "64", "63.875", "long-cell-demo-0005", "fifth row keeps going", "E5"],
    ["6", "24.75", "23.5", "128", "127.25", "table-buffer-0006", "sixth row overflow note", "F6"],
    ["7", "-31.125", "-30.0", "256", "255.5", "demo-column-0007", "seventh row more text", "G7"],
    ["8", "40.0", "39.25", "512", "511.75", "horizontal-test-08", "eighth row long payload", "H8"],
    ["9", "52.875", "51.75", "1024", "1023.875", "vertical-scroll-09", "ninth row visible later", "I9"],
    ["10", "66.5", "65.25", "2048", "2047.5", "editor-overflow-10", "tenth row for scrolling", "J10"],
    ["11", "81.0", "80.5", "4096", "4095.25", "beyond-screen-0011", "eleventh row keeps moving", "K11"],
    ["12", "96.25", "95.875", "8192", "8191.875", "final-overflow-0012", "twelfth row end sample", "L12"],
]


def _copy_table_keys():
    copied = []
    for row in getattr(form, "table_keys", []) or []:
        if isinstance(row, (list, tuple)):
            copied.append(list(row))
    return copied


def _capture_form_state():
    return {
        "ui_style": getattr(form, "ui_style", "classic"),
        "focus_inputs_only": getattr(form, "focus_inputs_only", False),
        "blink_cursor": getattr(form, "blink_cursor", False),
        "title": getattr(form, "title", ""),
        "input_cols": getattr(form, "input_cols", 19),
        "form_list": list(getattr(form, "form_list", [])),
        "input_list": dict(getattr(form, "input_list", {})),
        "menu_cursor": getattr(form, "menu_cursor", 0),
        "table_headers": list(getattr(form, "table_headers", [])),
        "table_keys": _copy_table_keys(),
        "table_row_count": getattr(form, "table_row_count", 0),
        "table_visible_rows": getattr(form, "table_visible_rows", 4),
        "table_visible_cols": getattr(form, "table_visible_cols", 5),
        "table_input_cols": getattr(form, "table_input_cols", 10),
        "table_cursor_row": getattr(form, "table_cursor_row", 0),
        "table_cursor_col": getattr(form, "table_cursor_col", 0),
        "table_row_offset": getattr(form, "table_row_offset", 0),
        "table_col_offset": getattr(form, "table_col_offset", 0),
        "table_show_button": getattr(form, "table_show_button", True),
        "table_button_text": getattr(form, "table_button_text", "Ok"),
    }


def _restore_form_state(previous):
    form.ui_style = previous["ui_style"]
    form.focus_inputs_only = previous["focus_inputs_only"]
    form.blink_cursor = previous["blink_cursor"]
    form.title = previous["title"]
    form.input_cols = previous["input_cols"]
    form.form_list = previous["form_list"]
    form.input_list = previous["input_list"]
    form.menu_cursor = previous["menu_cursor"]
    form.table_headers = previous["table_headers"]
    form.table_keys = previous["table_keys"]
    form.table_row_count = previous["table_row_count"]
    form.table_visible_rows = previous["table_visible_rows"]
    form.table_visible_cols = previous["table_visible_cols"]
    form.table_input_cols = previous["table_input_cols"]
    form.table_cursor_row = previous["table_cursor_row"]
    form.table_cursor_col = previous["table_cursor_col"]
    form.table_row_offset = previous["table_row_offset"]
    form.table_col_offset = previous["table_col_offset"]
    form.table_show_button = previous["table_show_button"]
    form.table_button_text = previous["table_button_text"]
    form.update()
    form_refresh.refresh(state=nav.current_state())


def _configure_demo():
    form.ui_style = "table"
    form.focus_inputs_only = False
    form.blink_cursor = True
    form.title = ""
    form.configure_table(
        headers=_HEADERS,
        row_count=len(_VALUES),
        values=_VALUES,
        visible_rows=4,
        visible_cols=5,
        input_cols=8,
        button_text="Ok",
        show_button=True,
    )
    form.table_cursor_row = 0
    form.table_cursor_col = 0
    form.update()
    form_refresh.refresh(state=nav.current_state())


def table_buffer_demo(db={}):
    keypad_state_manager_reset()
    current_app[0] = APP_NAME
    current_app[1] = APP_GROUP

    previous_form = _capture_form_state()
    try:
        _configure_demo()

        while True:
            inp = typer.start_typing()

            if inp == "home":
                app.set_app_name("home")
                app.set_group_name("root")
                return

            if inp == "back":
                app.set_app_name("installed_apps")
                app.set_group_name("root")
                return

            if inp in ("alpha", "beta"):
                keypad_state_manager(x=inp)
                form.update_buffer("")
            elif inp in ("ok", "exe"):
                app.set_app_name("installed_apps")
                app.set_group_name("root")
                return
            elif inp != "toolbox":
                form.update_buffer(inp)

            form_refresh.refresh(state=nav.current_state())
    finally:
        _restore_form_state(previous_form)
