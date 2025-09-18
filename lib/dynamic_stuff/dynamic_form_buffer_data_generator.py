# import _thread
from dynamic_stuff.dynamic_functions import get_data
from dynamic_stuff.dynamic_switches import data_generator_status
from dynamic_stuff.dynamic_data import menu_items_data
import time

def data_generator():

    while data_generator_status[0]==True:
        data = get_data()
        # menu_items_data.clear()
        # menu_items_data=data
        menu_items_data.clear()
        menu_items_data.update(data)
        for i in menu_items_data:
            form.form_list[i]=menu_items_data[i]
        print(form.form_list)
        time.sleep(0.1)

