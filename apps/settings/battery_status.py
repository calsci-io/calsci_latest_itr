import time
import json
from data_modules.object_handler import nav, keypad_state_manager, typer, keymap
from data_modules.object_handler import current_app
from process_modules import boot_up_data_update
from data_modules.object_handler import app
from machine import Pin, ADC
adc_pin = Pin(6)
adc = ADC(adc_pin)
adc.atten(ADC.ATTN_11DB)
adc.width(ADC.WIDTH_12BIT)
from sleeping_features import test_deep_sleep_awake
def battery_status():
    display.clear_display()
    # json_file = "/db/application_modules_app_list.json" 
    # with open(json_file, "r") as file:
    #     data = json.load(file)

    # menu_list = []
    # # for apps in data:
    # #     if apps["visibility"]:
    # #         menu_list.append(apps["name"])

    # menu.menu_list=menu_list
    # menu.update()
    # menu_refresh.refresh()
    try:
        while True:
            raw_value = adc.read()
            voltage = (raw_value / 4095) * 3.3
            menu_list = ["battery voltage:", str(round(2*voltage +0.220, 3))]
            menu.menu_list=menu_list
            menu.update()
            menu_refresh.refresh()
            # inp = typer.start_typing()

            # if inp == "back":
            #     pass
            # elif inp == "alpha" or inp == "beta":                        
            #     keypad_state_manager(x=inp)
            #     menu.update_buffer("")
            # elif inp =="ok":
            #     app.set_app_name(menu.menu_list[menu.menu_cursor])
            #     app.set_group_name("root")
            #     break

            # menu.update_buffer(inp)
            # menu_refresh.refresh(state=nav.current_state())
            time.sleep(1)
    except Exception as e:
        print(f"Error: {e}")
