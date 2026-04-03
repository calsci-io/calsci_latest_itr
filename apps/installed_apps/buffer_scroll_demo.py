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


APP_NAME = "buffer_scroll_demo"
APP_GROUP = "installed_apps"

_INITIAL_INPUTS = {
    "inp_0": "StartValue1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZ ",
    "inp_1": "Manual_Mode_For_Buffer_Test_001 ",
    "inp_2": "123456789012345678901234567890 ",
    "inp_3": "This vertical buffer should scroll cleanly inside the box ",
    "inp_4": "987654321098765432109876543210 ",
    "inp_5": "-31415926.5358979323 ",
    "inp_6": "-999999999999999999 ",
    "inp_7": "6.022e23 particles per mol buffer test ",
    "inp_8": "[]{}()<>+-=*/_symbols_buffer_test ",
    "inp_9": "AlphaBetaGammaDeltaMixedCaseInput ",
    "inp_10": "Long vertical text used to test overflow and cursor clipping ",
    "inp_11": "mm_per_sec_squared_123456789 ",
}

_PAGES = {
    "mixed": {
        "form_list": [
            "@link Numbers And Buttons Scroll Test",
            "@input_h Start",
            "inp_0",
            "@input_h Mode",
            "inp_1",
            "@input_v Steps",
            "inp_2",
            "@input_v Notes",
            "inp_3",
            "@button:center Open Numbers",
        ],
        "actions": {
            0: "numbers",
            9: "numbers",
        },
    },
    "numbers": {
        "form_list": [
            "@link Symbols And Mixed Text Scroll Test",
            "@input_h Long No",
            "inp_4",
            "@input_h Decimal",
            "inp_5",
            "@input_v Signed",
            "inp_6",
            "@input_v Sci Text",
            "inp_7",
            "@button:left Main",
            "@button:center Stay",
            "@button:right Symbols",
        ],
        "actions": {
            0: "symbols",
            9: "mixed",
            10: "numbers",
            11: "symbols",
        },
    },
    "symbols": {
        "form_list": [
            "@link Back To Main Mixed Buffer Page",
            "@input_h Symbols",
            "inp_8",
            "@input_h Mixed Case",
            "inp_9",
            "@input_v Long Text",
            "inp_10",
            "@input_v Units",
            "inp_11",
            "@button:right Done",
        ],
        "actions": {
            0: "mixed",
            9: "mixed",
        },
    },
}


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
    }


def _restore_form_state(previous):
    form.ui_style = previous["ui_style"]
    form.focus_inputs_only = previous["focus_inputs_only"]
    form.blink_cursor = previous["blink_cursor"]
    form.title = previous["title"]
    form.input_cols = previous["input_cols"]
    form.form_list = previous["form_list"]
    form.input_list = previous["input_list"]
    form.update()
    form.menu_cursor = previous["menu_cursor"]
    try:
        form._sync_input_view(prefer_end=False)
    except Exception:
        pass
    form_refresh.refresh(state=nav.current_state())


def _apply_page(page_name, input_values):
    page = _PAGES[page_name]
    form.input_list = input_values
    form.form_list = list(page["form_list"])
    form.update()
    display.clear_display()
    form_refresh.refresh(state=nav.current_state())


def _selected_page_action(page_name):
    return _PAGES.get(page_name, {}).get("actions", {}).get(getattr(form, "menu_cursor", 0))


def _open_page(page_name, input_values):
    if page_name not in _PAGES:
        return False
    _apply_page(page_name, input_values)
    return True


def buffer_scroll_demo(db={}):
    keypad_state_manager_reset()
    current_app[0] = APP_NAME
    current_app[1] = APP_GROUP

    previous_form = _capture_form_state()
    input_values = dict(_INITIAL_INPUTS)
    current_page = "mixed"
    page_history = []

    form.ui_style = "buffer"
    form.focus_inputs_only = False
    form.blink_cursor = True
    form.title = ""
    form.input_cols = 19

    try:
        _apply_page(current_page, input_values)

        while True:
            inp = typer.start_typing()

            if inp == "home":
                app.set_app_name("home")
                app.set_group_name("root")
                return

            if inp == "back":
                if page_history:
                    current_page = page_history.pop()
                    _apply_page(current_page, input_values)
                    continue
                app.set_app_name("installed_apps")
                app.set_group_name("root")
                return

            if inp in ("alpha", "beta"):
                keypad_state_manager(x=inp)
                form.update_buffer("")
            elif inp == "ok":
                target_page = _selected_page_action(current_page)
                if target_page and target_page != current_page:
                    page_history.append(current_page)
                    current_page = target_page
                    _open_page(current_page, input_values)
                    continue
                if target_page == current_page:
                    _open_page(current_page, input_values)
                    continue
            elif inp != "toolbox":
                form.update_buffer(inp)

            form_refresh.refresh(state=nav.current_state())
    finally:
        _restore_form_state(previous_form)
