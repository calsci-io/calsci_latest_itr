# Copyright (c) 2025 CalSci
# Licensed under the MIT License.

from data_modules.object_handler import app, current_app
from process_modules.navigation import NavigationRequest, register_app_entry


def _load_app_callable(app_name, group_name):
    module_name = "apps.{}.{}".format(group_name, app_name)
    module = __import__(module_name, None, None, (app_name,), 0)
    return getattr(module, app_name)


def app_runner():
    if (app.get_app_name() is None) or (app.get_group_name() is None):
        app.set_app_name("home")
        app.set_group_name("root")

    app_name = app.get_app_name()
    group_name = app.get_group_name()

    register_app_entry(app_name, group_name)
    current_app[0] = app_name
    current_app[1] = group_name

    app.set_none()

    try:
        _load_app_callable(app_name, group_name)()
    except NavigationRequest as nav:
        app.set_app_name(nav.app_name)
        app.set_group_name(nav.group_name)
