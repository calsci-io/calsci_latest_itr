import st7565 as display

try:
    import tools
    if hasattr(display, "graphics") and not hasattr(display.graphics, "pixels_changed"):
        display.graphics = tools.refresh(display.graphics, pixels_changed=200)
except Exception:
    pass

# Copyright (c) 2025 CalSci
# Licensed under the MIT License.

from data_modules.object_handler import app, current_app
from process_modules.navigation import NavigationRequest, register_app_entry

def app_runner():
    if (app.get_app_name() == None) or (app.get_group_name() == None):
        app.set_app_name("home")
        app.set_group_name("root")

    app_name = app.get_app_name()
    group_name = app.get_group_name()

    register_app_entry(app_name, group_name)
    current_app[0] = app_name
    current_app[1] = group_name

    imp_str = f"from apps.{group_name}.{app_name} import {app_name}"
    run_str = f"{app_name}()"

    app.set_none()

    try:
        exec(str(imp_str))
        exec(str(run_str))
    except NavigationRequest as nav:
        app.set_app_name(nav.app_name)
        app.set_group_name(nav.group_name)
