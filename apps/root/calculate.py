# import utime as time  # type:ignore
from math import *
import machine
from data_modules.object_handler import display, text, nav, text_refresh, typer, keypad_state_manager, keypad_state_manager_reset, current_app, app
from process_modules import boot_up_data_update
def calculate():
    global task
    keypad_state_manager_reset()
    display.clear_display()
    text.all_clear()
    text_refresh.new=True
    text_refresh.refresh()
    try:
        while True:

            x = typer.start_typing()
            if x == "back":
                current_app[0]="home"
                current_app[1] = "application_modules"
                break

            if (x == "ans" or x== "exe" or x == "ok") and text.text_buffer[0] != "𖤓":
                try:
                    # 1. Get the raw result from eval
                    raw_res = eval(text.text_buffer[:text.text_buffer_nospace])
                    
                    # 2. Format it using an f-string
                    res = f"= {raw_res:.12g}"
                except Exception as e:
                    res = "= Invalid Input"

                # text.all_clear()
                # display.clear_display()
                # text.update_buffer(res)
                text.update_buffer("")
                text_refresh.refresh(state=res)
                text_refresh.new=True
                continue

            elif x == "alpha" or x == "beta":                        
                keypad_state_manager(x=x)
                text.update_buffer("")
                text_refresh.refresh(state=nav.current_state())
                continue

            elif not (x == "ans" or x== "exe" or x == "ok"):
                text.update_buffer(x)
            
            if text.text_buffer[0] == "𖤓":
                # display.clear_display()
                text.all_clear()

            text_refresh.refresh(state=nav.current_state())
            # time.sleep(0.2)

    except Exception as e:
        print(f"Error: {e}")
