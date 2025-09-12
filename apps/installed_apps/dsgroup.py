"""
things to be made:
1. dynamic menu buffer uploader in thread
2. dynamic menu buffer data generator
3. dynamic global switch which is turned on by data generator and turned off by uploader
4. a switch for turning on the data generator on or off
5. if a function is given to the data generator then it will stay on or it will turn off
"""
from dynamic_stuff.dynamic_switches import *
from dynamic_stuff.dynamic_menu_buffer_uploader import uploader
from dynamic_stuff.dynamic_menu_buffer_data_generator import data_generator
import time
import json
from data_modules.object_handler import nav, keypad_state_manager, typer
from data_modules.object_handler import current_app
# from process_modules import boot_up_data_update
from data_modules.object_handler import app
import _thread
def dsgroup(db={}):
    global data_generator_status, new_upload
    display.clear_display()
    # json_file = "/db/application_modules_app_list.json" 
    # with open(json_file, "r") as file:
    #     data = json.load(file)

    # menu_list = []
    # for apps in data:
    #     if apps["visibility"]:
    #         menu_list.append(apps["name"])
    menu_list=["ab", "bc", "cd", "de", "ef", "fg", "gh", "hi", "ij", "jk", "kl"]
    menu.menu_list=menu_list
    menu.update()
    menu_refresh.refresh()
    try:
        while True:
            inp = typer.start_typing()
            if inp == "back":
                app.set_app_name("installed_apps")
                app.set_group_name("root")
                new_upload[0] = False
                data_generator_status[0]=False
                break
            elif inp =="ok":
                
                # app.set_app_name(menu.menu_list[menu.menu_cursor])
                # app.set_group_name("root")
                # break
                # if new_upload == False or data_generator_status == False:
                new_upload[0] = True
                data_generator_status[0] = True
                
                _thread.start_new_thread(data_generator, ())
                _thread.start_new_thread(uploader, ())
            menu.update_buffer(inp)
            menu_refresh.refresh()
            time.sleep(0.2)
    except Exception as e:
        print(f"Error: {e}")
