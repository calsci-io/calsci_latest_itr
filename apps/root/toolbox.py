import st7565 as display

try:
    import tools

    if hasattr(display, "graphics") and not hasattr(display.graphics, "pixels_changed"):
        display.graphics = tools.refresh(display.graphics, pixels_changed=200)
except Exception:
    pass

from data_modules.db_instance import fun_db
from data_modules.object_handler import (
    app,
    data_bucket,
    keypad_state_manager,
    menu,
    menu_refresh,
    nav,
    typer,
)


_PENDING_BUCKET_KEY = "_calculate_pending_action"


def _function_rows():
    rows = []
    for record in fun_db.all():
        name = str(record.get("name") or "").strip()
        if not name:
            continue
        variables = record.get("variables") or []
        rows.append(
            {
                "name": name,
                "arg_count": len(variables),
            }
        )
    return rows


def toolbox():
    all_functions = _function_rows()
    menu.menu_list = ["Functions"]
    if all_functions:
        menu.menu_list.extend(row["name"] for row in all_functions)
    else:
        menu.menu_list.append("No functions saved")

    menu.update()
    display.clear_display()
    menu_refresh.refresh(state=nav.current_state())

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
            if not all_functions or menu.menu_cursor <= 0:
                menu_refresh.refresh(state=nav.current_state())
                continue

            selected = all_functions[menu.menu_cursor - 1]
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
