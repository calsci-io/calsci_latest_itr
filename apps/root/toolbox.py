import time
import json
from data_modules.object_handler import nav, keypad_state_manager, typer, display
from data_modules.object_handler import text
# from process_modules import boot_up_data_update
from data_modules.object_handler import app
from data_modules.db_instance import fun_db

from tinydb import TinyDB, Query
Function = Query()
# Initialize the database, which will use 'db.json' to store data
# db = TinyDB('db/functions_data.json')

def toolbox():
    display.clear_display()
    menu.menu_list=[row["name"] for row in fun_db.all()]
    menu.update()
    menu_refresh.refresh()
    text.retain_data=True
    try:
        while True:
            inp = typer.start_typing()
            if inp == "back":
                app.set_app_name("calculate")
                app.set_group_name("root")
                text.update_buffer("")
                break
            elif inp == "alpha" or inp == "beta":                        
                keypad_state_manager(x=inp)
                menu.update_buffer("")
            elif inp =="ok":
                # app.set_app_name(menu.menu_list[menu.menu_cursor])
                text.update_buffer(menu.menu_list[menu.menu_cursor])
                app.set_app_name("calculate")
                app.set_group_name("root")
                break
            menu.update_buffer(inp)
            menu_refresh.refresh(state=nav.current_state())
            # time.sleep(0.2)
    except Exception as e:
        print(f"Error: {e}")
