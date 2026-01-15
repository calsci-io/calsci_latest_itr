from data_modules.object_handler import app

def app_runner():
    # name=app.get_app_name()
    # group=app.get_group_name()
    # text_refresh.new=True
    if (app.get_app_name() == None) or (app.get_group_name() == None):
        app.set_app_name("home")
        app.set_group_name("root")
        # app.set_app_name("battery_status")
        # app.set_group_name("settings")
    
    imp_str=f"from apps.{app.get_group_name()}.{app.get_app_name()} import {app.get_app_name()}"
    run_str=f"{app.get_app_name()}()"
    
    app.set_none()

    exec(str(imp_str))
    exec(str(run_str))
