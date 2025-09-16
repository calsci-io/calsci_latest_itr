from data_modules.object_handler import display, form, nav, form_refresh, typer, keypad_state_manager, keypad_state_manager_reset
from data_modules.object_handler import app
# import urequests # type: ignore
import gc
import time
from sleeping_features import get_sleep_time, update_sleep_time

def sleep_after(db={}):
    print("start of sleep_after", gc.mem_free())
    keypad_state_manager_reset()
    global display, form, form_refresh, typer, nav, current_app
    display.clear_display()
    form.input_list={"inp_0": str(int(get_sleep_time()/60000))}
    form.form_list=["sleep after minutes:", "inp_0"]
    form.update()
    form_refresh.refresh()
    while True:
        inp = typer.start_typing()
        if inp == "back":
            app.set_app_name("settings")
            app.set_group_name("root")
            break

        elif inp == "ok":
            tm=form.inp_list()["inp_0"]
            try:
                if int(tm)<=14400:
                    update_sleep_time(int(tm)*60000)
                    print("db time = ",get_sleep_time(), "form input time = ", tm)
                    form.form_list=["sleep after minutes:", "inp_0", "updated successfully"]
                    form.update()
                    form_refresh.refresh()
                elif int(tm)>14400:
                    form.form_list=["sleep after minutes:", "inp_0", "maximum is 14400"]
                    form.update()
                    form_refresh.refresh()
            except:
                form.form_list=["sleep after minutes:", "inp_0", "wrong input"]
                form.update()
                form_refresh.refresh()
        elif inp == "alpha" or inp == "beta":
            keypad_state_manager(x=inp)
            form.update_buffer("")
        elif inp not in ["alpha", "beta", "ok"]:
            form.update_buffer(inp)
            if "updated successfully" in form.form_list:
                form.form_list.pop()
                form.update()
                form_refresh.refresh()
        form_refresh.refresh(state=nav.current_state())
    
        time.sleep(0.1)
