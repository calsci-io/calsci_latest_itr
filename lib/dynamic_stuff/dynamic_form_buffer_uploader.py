from dynamic_stuff.dynamic_switches import new_upload
from dynamic_stuff.dynamic_data import menu_items_data
from data_modules.object_handler import nav, chrs
# from data_modules.object_handler import menu
# from data_modules.object_handler import chrs
import time
def refresh(state="default"):
    form.refresh_rows=(0,form.actual_rows)
    form_refresh.refresh()
    # # buf=form.buffer()
    # buf=menu_items_data.values()
    # # ref_rows=form.ref_ar()
    # ref_rows=menu_items_data.keys()
    # for i in ref_rows:
    #     if i in range(form.menu_display_position,form.menu_display_position+form.rows):
    #         display.set_page_address(i-form.menu_display_position)
    #         display.set_column_address(0)
    #         if "inp_" in buf[i]:
    #             buf_current="=>"+form.inp_list()[form.buffer()[i]][form.inp_display_position():form.inp_display_position()+form.inp_cols()]
    #         else:
    #             buf_current = buf[i]
    #         if len(buf_current)<form.inp_cols():
    #                 buf_current+=" "*(form.inp_cols()-len(buf_current)+2)
    #         j_counter=0
    #         for j in buf_current:
    #             if i == form.cursor() and "inp_" not in buf[i]:
    #                 chtr_byte_data=chrs.invert_letter(j)
    #                 cursor_line=0b11111111
    #                 for k in chtr_byte_data:
    #                     display.write_data(k)
    #                 display.write_data(cursor_line)
    #             elif i == form.cursor() and "inp_" in buf[i]:
    #                 if j_counter+form.inp_display_position()==form.inp_cursor()+2:
    #                     chtr_byte_data=chrs.invert_letter(j)
    #                     cursor_line=0b11111111
    #                     for k in chtr_byte_data:
    #                         display.write_data(k)
    #                     display.write_data(cursor_line)
    #                 else:
    #                     chtr_byte_data=chrs.Chr2bytes(j)
    #                     cursor_line=0b00000000
    #                     for k in chtr_byte_data:
    #                         display.write_data(k)
    #                     display.write_data(cursor_line)
    #             else:
    #                 chtr_byte_data=chrs.Chr2bytes(j)
    #                 cursor_line=0b00000000
    #                 for k in chtr_byte_data:
    #                     display.write_data(k)
    #                 display.write_data(cursor_line)
    #             j_counter+=1
        
    #     display.set_page_address(7)
    #     display.set_column_address(0)
    #     j_counter=0
    #     for j in state:
    #         chtr=j
    #         chtr_byte_data=chrs.invert_letter(chtr)
    #         cursor_line=0b11111111
    #         for k in chtr_byte_data:
    #             display.write_data(k)
    #         display.write_data(cursor_line)
    #         j_counter+=1

def uploader():
    print("starting dynamic form buffer uploader thread")
    while new_upload[0]==True:
        # data = get_data()
        # for i in data.keys():
        #     if i in range(menu.menu_display_position,menu.menu_display_position+menu.rows):
        #         pass
        refresh(state=nav.current_state())
        print("running dynamic form buffer uploader thread")
        print(form.form_list)
        print("ref ar = ", form.ref_ar())
        print(menu_items_data)

        time.sleep(0.5)
    print("stopping dynamic form buffer uploader thread")