import st7565 as display

try:
    import tools
    if hasattr(display, "graphics") and not hasattr(display.graphics, "pixels_changed"):
        display.graphics = tools.refresh(display.graphics, pixels_changed=200)
except Exception:
    pass

from math import *
from data_modules.object_handler import display, text, nav, text_refresh, typer, keypad_state_manager, keypad_state_manager_reset, current_app, app, keymap
from data_modules.db_instance import fun_db
from data_modules.object_handler import data_bucket

def build_function(func_def, safe_globals):
    vars_ = func_def["variables"]
    expr = func_def["expression"]

    def generated_function(*args):
        if len(args) != len(vars_):
            raise ValueError("Wrong number of arguments")

        local_scope = {}
        for i in range(len(vars_)):
            local_scope[vars_[i]] = args[i]

        return eval(expr, safe_globals, local_scope)

    return generated_function

# from math import sin, cos, tan, sqrt, radians

FUNCTIONS = {}

# SAFE_GLOBALS = {
#     "__builtins__": {},
#     "sin": sin,
#     "cos": cos,
#     "tan": tan,
#     "sqrt": sqrt,
#     "radians": radians,


# }

ans=[0,0]

LOCKABLE_KEYPAD_STATES = ("a", "A", "b")
ALPHA_KEYPAD_STATES = ("a", "A")

SAFE_GLOBALS = {
    "__builtins__": {},

    # trig + inverse trig
    "sin": sin,
    "cos": cos,
    "tan": tan,
    "asin": asin,
    "acos": acos,
    "atan": atan,
    "atan2": atan2,

    # hyperbolic
    "sinh": sinh,
    "cosh": cosh,
    "tanh": tanh,
    "asinh": asinh,
    "acosh": acosh,
    "atanh": atanh,

    # exponentials/logs
    "exp": exp,
    "expm1": expm1,
    "log": log,
    "log10": log10,
    "log2": log2,
    "pow": pow,
    "sqrt": sqrt,

    # rounding/parts
    "ceil": ceil,
    "floor": floor,
    "trunc": trunc,
    "modf": modf,
    "frexp": frexp,
    "ldexp": ldexp,
    "fmod": fmod,

    # misc math
    "fabs": fabs,
    "copysign": copysign,
    "degrees": degrees,
    "radians": radians,

    # special functions
    "erf": erf,
    "erfc": erfc,
    "gamma": gamma,
    "lgamma": lgamma,

    # checks
    "isfinite": isfinite,
    "isinf": isinf,
    "isnan": isnan,

    # constants
    "e": e,
    "pi": pi,
    "ans":ans[0]
}


def load_all_functions():
    FUNCTIONS.clear()

    for row in fun_db.all():
        name = row.get("name")
        variables = row.get("variables")
        expression = row.get("expression")

        if not name or not variables or not expression:
            continue  # skip broken entries

        func_def = {
            "variables": variables,
            "expression": expression
        }

        FUNCTIONS[name] = build_function(func_def, SAFE_GLOBALS)
        SAFE_GLOBALS[name] = FUNCTIONS[name]  # 👈 critical


def _set_keypad_mode(state):
    keymap.key_change(state=state)
    nav.state_change(state=state)


def _calculate_nav_state(mode_locked):
    current_state = nav.current_state().strip()
    if mode_locked and keymap.state in LOCKABLE_KEYPAD_STATES:
        return "{} locked".format(current_state)
    return nav.current_state()


# from process_modules import boot_up_data_update
# import uasyncio as asyncio
# from test_async import main, cancel_task
# asyncio.run(main())
# from 
# from test_thread import run_espnow_message, end_espnow_task
task=None
def calculate():
    global ans
    load_all_functions()
    global task
    mode_locked = False
    keypad_state_manager_reset()
    display.clear_display()
    if text.retain_data == False:
        text.all_clear()
    else:
        text.refresh_area=(0, text.rows * text.cols)
        text.retain_data = False
    text_refresh.new=True
    text_refresh.refresh(state=_calculate_nav_state(mode_locked))
    task=None
    try:
        while True:

            x = typer.start_typing()
            current_mode = keymap.state
            if x == "back":
                current_app[0]="home"
                current_app[1] = "application_modules"
                break

            if x == "lock":
                if current_mode in LOCKABLE_KEYPAD_STATES:
                    if mode_locked:
                        mode_locked = False
                        keypad_state_manager_reset()
                    else:
                        mode_locked = True
                    text.update_buffer("")
                    text_refresh.refresh(state=_calculate_nav_state(mode_locked))
                    continue

                text_refresh.refresh(state=_calculate_nav_state(mode_locked))
                continue

            if (x== "exe" or x == "ok") and text.text_buffer[0] != "𖤓":
                try:
                    # 1. Get the raw result from eval
                    raw_res = eval(text.text_buffer[:text.text_buffer_nospace], SAFE_GLOBALS)
                    
                    # 2. Format it using an f-string
                    res = f"= {raw_res:.12g}"
                    ans[0]=raw_res
                    SAFE_GLOBALS["ans"]=ans[0]
                except Exception as e:
                    res = str(e)
                    if "error_msg" in data_bucket.keys():
                        data_bucket.pop("error_msg")
                    data_bucket["error_msg"]=res
                    print("calculate", data_bucket["error_msg"])
                    data_bucket["error_parent_app_name"]="calculate"
                    data_bucket["error_parent_group_name"]="root"
                    app.set_app_name("error_screen")
                    app.set_group_name("root")
                    break
                print(res)

                # text.all_clear()
                # display.clear_display()
                # text.update_buffer(res)
                text.update_buffer("")
                text_refresh.refresh(state=res)
                text_refresh.new=True
                continue

            elif x == "alpha":
                if mode_locked and current_mode in ALPHA_KEYPAD_STATES:
                    mode_locked = False
                    keypad_state_manager_reset()
                else:
                    mode_locked = False
                    if current_mode in ALPHA_KEYPAD_STATES:
                        keypad_state_manager_reset()
                    else:
                        _set_keypad_mode("a")
                text.update_buffer("")
                text_refresh.refresh(state=_calculate_nav_state(mode_locked))
                continue

            elif x == "beta":
                if mode_locked and current_mode == "b":
                    mode_locked = False
                    keypad_state_manager_reset()
                else:
                    mode_locked = False
                    if current_mode == "b":
                        keypad_state_manager_reset()
                    else:
                        _set_keypad_mode("b")
                text.update_buffer("")
                text_refresh.refresh(state=_calculate_nav_state(mode_locked))
                continue
            elif x == "caps":
                if current_mode in ALPHA_KEYPAD_STATES:
                    if current_mode == "a":
                        _set_keypad_mode("A")
                    else:
                        _set_keypad_mode("a")
                else:
                    keypad_state_manager(x="A")
                text.update_buffer("")
                text_refresh.refresh(state=_calculate_nav_state(mode_locked))
                continue
            
            elif x == "toolbox":
                app.set_app_name("toolbox")
                app.set_group_name("root")
                break

            elif not (x== "exe" or x == "ok"):
                text.update_buffer(x)

            if (not mode_locked) and keymap.state in LOCKABLE_KEYPAD_STATES:
                keypad_state_manager_reset()
                text.update_buffer("")
                text_refresh.refresh(state=_calculate_nav_state(mode_locked))
                continue
            
            if text.text_buffer[0] == "𖤓":
                # display.clear_display()
                text.all_clear()
            

            text_refresh.refresh(state=_calculate_nav_state(mode_locked))
            # time.sleep(0.2)

    except Exception as e:
        print(f"Error: {e}")
