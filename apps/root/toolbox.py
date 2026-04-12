import st7565 as display

try:
    import tools

    if hasattr(display, "graphics") and not hasattr(display.graphics, "pixels_changed"):
        display.graphics = tools.refresh(display.graphics, pixels_changed=200)
except Exception:
    pass

from apps.root.function_store import list_default_functions, list_user_functions
from data_modules.object_handler import app, data_bucket, keypad_state_manager, menu, menu_refresh, nav, typer


_PENDING_BUCKET_KEY = "_calculate_pending_action"
SECTION_USER = "[User Defined]"
SECTION_DEFAULT = "[Default Functions]"
_TOOLBOX_INPUT_POLL_SEC = 0.01


def _push_toolbox_poll_delay():
    previous_delay = getattr(typer, "debounce_delay_time", None)
    if previous_delay is not None:
        typer.debounce_delay_time = _TOOLBOX_INPUT_POLL_SEC
    return previous_delay


def _restore_toolbox_poll_delay(previous_delay):
    if previous_delay is not None:
        typer.debounce_delay_time = previous_delay


def _toolbox_entries():
    labels = [SECTION_USER]
    selected_rows = {}

    user_rows = list_user_functions()
    if user_rows:
        for row in user_rows:
            name = str(row.get("name") or "").strip()
            if name == "":
                continue
            selected_rows[len(labels)] = {
                "name": name,
                "arg_count": len(row.get("variables") or []),
            }
            labels.append(name)
    else:
        labels.append("No user functions")

    labels.append(SECTION_DEFAULT)

    default_rows = list_default_functions()
    if default_rows:
        for row in default_rows:
            name = str(row.get("name") or "").strip()
            if name == "":
                continue
            selected_rows[len(labels)] = {
                "name": name,
                "arg_count": len(row.get("variables") or []),
            }
            labels.append(name)
    else:
        labels.append("No default functions")

    return labels, selected_rows


def toolbox():
    previous_delay = _push_toolbox_poll_delay()
    menu_labels, selected_rows = _toolbox_entries()
    menu.menu_list = menu_labels

    menu.update()
    if selected_rows and menu.menu_cursor not in selected_rows:
        first_selectable = min(selected_rows.keys())
        menu.menu_cursor = first_selectable
        max_display = max(0, len(menu.menu_list) - menu.menu_display_size)
        menu.menu_display_position = min(first_selectable, max_display)
        if menu.menu_cursor < menu.menu_display_position:
            menu.menu_display_position = menu.menu_cursor
        elif menu.menu_cursor >= menu.menu_display_position + menu.menu_display_size:
            menu.menu_display_position = menu.menu_cursor - menu.menu_display_size + 1
        menu.display_buffer = menu.menu_list[
            menu.menu_display_position : menu.menu_display_position + menu.menu_display_size
        ]
        menu.display_cursor = menu.menu_cursor - menu.menu_display_position
        menu.refresh_rows = (0, menu.menu_display_size)
    display.clear_display()
    menu_refresh.refresh(state=nav.current_state())

    try:
        while True:
            inp = typer.start_typing()

            if inp == "back":
                app.set_app_name("calculate")
                app.set_group_name("root")
                return

            if inp in ("alpha", "beta"):
                keypad_state_manager(x=inp)
                menu.update_buffer("")
                menu_refresh.refresh(state=nav.current_state())
                continue

            if inp == "ok":
                selected = selected_rows.get(menu.menu_cursor)
                if selected is None:
                    menu_refresh.refresh(state=nav.current_state())
                    continue

                data_bucket[_PENDING_BUCKET_KEY] = {
                    "type": "insert_function",
                    "name": selected["name"],
                    "arg_count": selected["arg_count"],
                }
                app.set_app_name("calculate")
                app.set_group_name("root")
                return

            menu.update_buffer(inp)
            menu_refresh.refresh(state=nav.current_state())
    finally:
        _restore_toolbox_poll_delay(previous_delay)
