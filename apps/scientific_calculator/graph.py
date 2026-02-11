# Copyright (c) 2025 CalSci
# Licensed under the MIT License.
# Optimized version with partial refresh for faster rendering

from mocking import framebuf # type: ignore
import math
import utime as time  # type:ignore
from data_modules.object_handler import display, form, nav, text, text_refresh, form_refresh, typer, keypad_state_manager, keypad_state_manager_reset
from data_modules.object_handler import current_app
import gc

eval_globals = {
    # Functions
    'sin': math.sin, 'cos': math.cos, 'tan': math.tan,
    'asin': math.asin, 'acos': math.acos, 'atan': math.atan,
    'atan2': math.atan2, 'ceil': math.ceil, 'copysign': math.copysign,
    'degrees': math.degrees, 'exp': math.exp, 'fabs': math.fabs,
    'floor': math.floor, 'fmod': math.fmod, 'frexp': math.frexp,
    'ldexp': math.ldexp, 'log': math.log, 'modf': math.modf,
    'pow': math.pow, 'radians': math.radians, 'sqrt': math.sqrt,
    'trunc': math.trunc,
    # Constants
    'pi': math.pi, 'e': math.e,
}

# Lightweight config
ZOOM_IN = 0.8
ZOOM_OUT = 1.25
PAN_SHIFT = 0.15
SAMPLES_PER_PX = 2

def format_number(value):
    """Format number for display."""
    pi_multiple = value / math.pi
    if abs(pi_multiple - round(pi_multiple)) < 0.001:
        multiple = round(pi_multiple)
        if multiple == 0:
            return "0 "
        elif multiple == 1:
            return "pi "
        elif multiple == -1:
            return "-pi "
        else:
            return str(int(multiple)) + "*pi "
    if abs(value) < 0.01:
        return "0 "
    elif abs(value) < 100:
        return str(round(value, 2)) + " "
    else:
        return str(int(value)) + " "

class SmallCharacters:
    """3x5 font for axis labels."""
    Chr3x5_data = {
        "x": [0x05, 0x02, 0x05], "m": [0x07, 0x06, 0x07],
        "i": [0x00, 0x17, 0x00], "n": [0x07, 0x04, 0x07],
        "a": [0x17, 0x15, 0x1F], "_": [0x01, 0x01, 0x01],
        " ": [0x00, 0x00, 0x00], "y": [0x1D, 0x05, 0x1F],
        "0": [0x0E, 0x11, 0x0E], "1": [0x04, 0x0C, 0x04],
        "2": [0x1E, 0x02, 0x1F], "3": [0x1E, 0x0E, 0x1F],
        "4": [0x11, 0x1F, 0x01], "5": [0x1F, 0x0E, 0x1F],
        "6": [0x0E, 0x14, 0x0E], "7": [0x1F, 0x02, 0x04],
        "8": [0x0E, 0x0E, 0x0E], "9": [0x0E, 0x0F, 0x0E],
        ".": [0x00, 0x00, 0x04], "-": [0x00, 0x1F, 0x00],
    }

    @classmethod
    def get_char(cls, char):
        return cls.Chr3x5_data.get(char, [0x1F, 0x1F, 0x1F])

def draw_small_text(fb, text, x, y):
    """Draw text using 3x5 font."""
    for char in text:
        char_data = SmallCharacters.get_char(char)
        for col in range(3):
            byte = char_data[col]
            for row in range(5):
                if byte & (1 << (4 - row)):
                    fb.pixel(x + col, y + row, 1)
        x += 4

class MediumDigits:
    """5x7 font for cursor coordinates."""
    data = {
        " ": [0x00, 0x00, 0x00, 0x00, 0x00],
        "0": [0x3E, 0x51, 0x49, 0x45, 0x3E],
        "1": [0x00, 0x42, 0x7F, 0x40, 0x00],
        "2": [0x42, 0x61, 0x51, 0x49, 0x46],
        "3": [0x21, 0x41, 0x45, 0x4B, 0x31],
        "4": [0x18, 0x14, 0x12, 0x7F, 0x10],
        "5": [0x27, 0x45, 0x45, 0x45, 0x39],
        "6": [0x3C, 0x4A, 0x49, 0x49, 0x30],
        "7": [0x01, 0x71, 0x09, 0x05, 0x03],
        "8": [0x36, 0x49, 0x49, 0x49, 0x36],
        "9": [0x06, 0x49, 0x49, 0x29, 0x1E],
        ".": [0x00, 0x60, 0x60, 0x00, 0x00],
        "-": [0x08, 0x08, 0x08, 0x08, 0x08],
        "x": [0x44, 0x28, 0x10, 0x28, 0x44],
        "y": [0x0C, 0x50, 0x50, 0x50, 0x3C],
        "u": [0x3C, 0x40, 0x40, 0x20, 0x7C],
        "n": [0x7C, 0x08, 0x04, 0x04, 0x78],
        "d": [0x38, 0x44, 0x44, 0x48, 0x7F],
        "e": [0x38, 0x54, 0x54, 0x54, 0x18],
        "f": [0x08, 0x7E, 0x09, 0x01, 0x02],
    }

    @classmethod
    def get_char(cls, char):
        return cls.data.get(char, cls.data[" "])

def draw_medium_text(fb, text, x, y):
    """Draw text using 5x7 font."""
    for char in text:
        char_data = MediumDigits.get_char(char)
        for col in range(5):
            byte = char_data[col]
            for row in range(7):
                if byte & (1 << row):
                    fb.pixel(x + col, y + row, 1)
        x += 6

class CursorState:
    """Lightweight cursor state."""
    def __init__(self):
        self.active = False
        self.x_pixel = 64
        self.prev_x_pixel = 64

    def toggle(self):
        self.active = not self.active
        self.prev_x_pixel = self.x_pixel

    def move(self, direction, width=128):
        """Move cursor and return True if position changed."""
        self.prev_x_pixel = self.x_pixel
        if direction == 'left' and self.x_pixel > 0:
            self.x_pixel -= 1
            return True
        elif direction == 'right' and self.x_pixel < width - 1:
            self.x_pixel += 1
            return True
        return False

def safe_eval(func, exp_str, x):
    """Safely evaluate function."""
    try:
        y = func(exp_str, x)
        if y != y:  # NaN check
            return None
        if abs(y) > 1e10:
            return None
        return y
    except:
        return None

def draw_cursor(fb, cursor, bounds, func, exp_str, width=128, height=56):
    """Draw cursor line and coordinates - marks dirty region."""
    if not cursor.active:
        return

    x_range = bounds['x_max'] - bounds['x_min']
    if x_range == 0 or width < 2:
        return

    # Calculate x coordinate
    x_coord = bounds['x_min'] + (cursor.x_pixel / (width - 1)) * x_range

    # Mark cursor area as dirty (vertical line + text areas)
    fb._mark_dirty(cursor.x_pixel, 0, 1, height + 8)  # Cursor line + text area
    fb._mark_dirty(0, height, width, 8)  # Full text area at bottom

    # Draw vertical line
    fb.vline(cursor.x_pixel, 0, height, 1)

    # Format and display coordinates
    def fmt(val, prefix):
        if abs(val) < 0.01:
            return prefix + " 0"
        elif abs(val) < 10:
            s = prefix + str(round(val, 2))
        else:
            s = prefix + str(int(val))
        return s[:8]

    x_str = fmt(x_coord, "x")
    draw_medium_text(fb, x_str, 2, height + 1)

    # Evaluate y
    y_coord = safe_eval(func, exp_str, x_coord)
    if y_coord is not None:
        y_str = fmt(y_coord, "y")
        draw_medium_text(fb, y_str, width - 42, height + 1)
    else:
        draw_medium_text(fb, "y undef", width - 42, height + 1)

def plot_function(fb, func, exp_str, x_min, x_max, y_min, y_max, width=128, height=64, cursor=None):
    """Optimized plotting - marks entire plot area as dirty."""
    global eval_globals

    plot_height = height

    if width < 2 or plot_height < 2:
        return

    # Mark entire plot area as dirty
    fb._mark_dirty(0, 0, width, plot_height)

    x_range = x_max - x_min
    y_range = y_max - y_min
    if x_range == 0 or y_range == 0:
        return

    x_scale = x_range / (width - 1)
    y_scale = y_range / (plot_height - 1)

    def map_y(y_val):
        """Map y value to pixel."""
        py = int((y_max - y_val) / y_scale + 0.5)
        if py < 0 or py >= plot_height:
            return None
        return py

    # Draw axes
    x_axis_y = int((y_max / y_scale) + 0.5) if y_min <= 0 <= y_max else -1
    y_axis_x = int((0 - x_min) / x_scale + 0.5) if x_min <= 0 <= x_max else -1

    if 0 <= x_axis_y < plot_height:
        fb.hline(0, x_axis_y, width, 1)
    if 0 <= y_axis_x < width:
        fb.vline(y_axis_x, 0, plot_height, 1)

    # Optimized plotting: stream processing
    total_samples = width * SAMPLES_PER_PX
    step = x_range / (total_samples - 1)

    prev_x_px = None
    prev_y_px = None
    prev_y_val = None

    for i in range(total_samples):
        x_val = x_min + i * step
        y_val = safe_eval(func, exp_str, x_val)

        if y_val is None:
            prev_x_px = None
            prev_y_px = None
            prev_y_val = None
            continue

        if y_val < y_min or y_val > y_max:
            prev_x_px = None
            prev_y_px = None
            prev_y_val = None
            continue

        x_px = int((x_val - x_min) / x_scale + 0.5)
        y_px = map_y(y_val)

        if y_px is None or x_px < 0 or x_px >= width:
            prev_x_px = None
            prev_y_px = None
            prev_y_val = None
            continue

        fb.pixel(x_px, y_px, 1)

        if prev_x_px is not None and prev_y_px is not None:
            dy = abs(y_px - prev_y_px)
            if dy < plot_height // 3:
                fb.line(prev_x_px, prev_y_px, x_px, y_px, 1)

        prev_x_px = x_px
        prev_y_px = y_px
        prev_y_val = y_val

    # Draw cursor if active
    if cursor and cursor.active:
        draw_cursor(fb, cursor, {'x_min': x_min, 'x_max': x_max, 'y_min': y_min, 'y_max': y_max},
                   func, exp_str, width, plot_height)

def get_bounds():
    """Get bounds from form."""
    return {
        'x_min': eval(form.inp_list()["inp_1"], eval_globals),
        'x_max': eval(form.inp_list()["inp_2"], eval_globals),
        'y_min': eval(form.inp_list()["inp_3"], eval_globals),
        'y_max': eval(form.inp_list()["inp_4"], eval_globals),
    }

def update_bounds(bounds):
    """Update form with new bounds."""
    form.input_list["inp_1"] = format_number(bounds['x_min'])
    form.input_list["inp_2"] = format_number(bounds['x_max'])
    form.input_list["inp_3"] = format_number(bounds['y_min'])
    form.input_list["inp_4"] = format_number(bounds['y_max'])

def apply_zoom(bounds, factor):
    """Apply zoom factor to bounds."""
    x_range = bounds['x_max'] - bounds['x_min']
    y_range = bounds['y_max'] - bounds['y_min']
    x_center = (bounds['x_min'] + bounds['x_max']) / 2
    y_center = (bounds['y_min'] + bounds['y_max']) / 2

    new_x_range = x_range * factor
    new_y_range = y_range * factor

    return {
        'x_min': x_center - new_x_range / 2,
        'x_max': x_center + new_x_range / 2,
        'y_min': y_center - new_y_range / 2,
        'y_max': y_center + new_y_range / 2,
    }

def apply_pan(bounds, direction):
    """Apply pan in given direction."""
    x_range = bounds['x_max'] - bounds['x_min']
    y_range = bounds['y_max'] - bounds['y_min']
    shift = PAN_SHIFT

    new_bounds = bounds.copy()

    if direction == 'up':
        shift_amount = y_range * shift
        new_bounds['y_min'] += shift_amount
        new_bounds['y_max'] += shift_amount
    elif direction == 'down':
        shift_amount = y_range * shift
        new_bounds['y_min'] -= shift_amount
        new_bounds['y_max'] -= shift_amount
    elif direction == 'left':
        shift_amount = x_range * shift
        new_bounds['x_min'] -= shift_amount
        new_bounds['x_max'] -= shift_amount
    elif direction == 'right':
        shift_amount = x_range * shift
        new_bounds['x_min'] += shift_amount
        new_bounds['x_max'] += shift_amount

    return new_bounds

def replot(fb, fb_buf, exp_str, bounds, cursor, cache_buf=None):
    """Clear and replot graph with partial refresh support."""
    start_time = time.ticks_ms()

    fb.fill(0)
    use_cursor = cursor and cursor.active

    # Plot without cursor first
    plot_function(fb, polynom1, exp_str,
                  bounds['x_min'], bounds['x_max'],
                  bounds['y_min'], bounds['y_max'],
                  128, 64 if not use_cursor else 56, None)

    # Cache clean graph
    if cache_buf is not None:
        cache_buf[:] = fb_buf

    # Add cursor
    if use_cursor:
        draw_cursor(fb, cursor, bounds, polynom1, exp_str, 128, 56)

    # PARTIAL REFRESH: Only update dirty region
    if fb.is_dirty:
        dirty_region = fb.get_dirty_region()
        if dirty_region:
            x, y, w, h = dirty_region
            print(f"Partial update: x={x}, y={y}, w={w}, h={h}")
            # If your display supports partial update:
            # display.partial_update(x, y, w, h, fb_buf)
            # Otherwise fall back to full update:
            display.clear_display()
            display.graphics(fb_buf)
        fb.clear_dirty()
    else:
        display.clear_display()
        display.graphics(fb_buf)

    elapsed = time.ticks_diff(time.ticks_ms(), start_time)
    print("Replot:", elapsed, "ms")

def update_cursor_only(fb, fb_buf, cache_buf, cursor, bounds, exp_str):
    """Fast cursor update with partial refresh."""
    start_time = time.ticks_ms()

    # Restore clean graph from cache
    fb_buf[:] = cache_buf
    
    # Clear dirty state before drawing cursor
    fb.clear_dirty()

    # Draw cursor (this marks dirty region)
    if cursor.active:
        draw_cursor(fb, cursor, bounds, polynom1, exp_str, 128, 56)

    # PARTIAL REFRESH: Only update cursor area
    if fb.is_dirty:
        dirty_region = fb.get_dirty_region()
        if dirty_region:
            x, y, w, h = dirty_region
            print(f"Cursor partial: x={x}, y={y}, w={w}, h={h}")
            # If your display supports partial update:
            # display.partial_update(x, y, w, h, fb_buf)
            # Otherwise:
            display.graphics(fb_buf)
        fb.clear_dirty()
    else:
        display.graphics(fb_buf)

    elapsed = time.ticks_diff(time.ticks_ms(), start_time)
    print("Cursor update:", elapsed, "ms")

def graph(db={}):
    """Main graph application with partial refresh."""
    print("Graph start, mem:", gc.mem_free())
    keypad_state_manager_reset()

    global display, form, form_refresh, typer, nav, current_app, eval_globals

    form.input_list = {
        "inp_0": "x*sin(x) ",
        "inp_1": "-20 ", "inp_2": "20 ",
        "inp_3": "-10 ", "inp_4": "10 "
    }
    form.form_list = [
        "enter function:f(x)", "inp_0",
        "enter x_min:", "inp_1", "enter x_max:", "inp_2",
        "enter y_min:", "inp_3", "enter y_max:", "inp_4"
    ]
    form.update()
    form_refresh.refresh()

    buffer1 = bytearray((128 * 64) // 8)
    fb1 = framebuf.FrameBuffer(buffer1, 128, 64, framebuf.MONO_VLSB)
    cache_buffer = bytearray((128 * 64) // 8)
    cursor = CursorState()

    while True:
        inp = typer.start_typing()

        if inp == "back":
            del buffer1, fb1, cursor, cache_buffer
            gc.collect()
            current_app[0] = "scientific_calculator"
            current_app[1] = "application_modules"
            break

        elif inp == "home":
            del buffer1, fb1, cursor, cache_buffer
            gc.collect()
            current_app[0] = "home"
            current_app[1] = "root"
            break

        elif inp == "ok":
            try:
                bounds = get_bounds()
                replot(fb1, buffer1, form.inp_list()["inp_0"], bounds, cursor, cache_buffer)
            except Exception as e:
                print("Plot error:", e)
                continue

            print("After plot, mem:", gc.mem_free())

            # Interactive mode
            while True:
                inp_breaker = typer.start_typing()

                if inp_breaker in ("a", "A", "module", "copy"):
                    cursor.toggle()
                    replot(fb1, buffer1, form.inp_list()["inp_0"], bounds, cursor, cache_buffer)

                elif inp_breaker == "+":
                    bounds = apply_zoom(bounds, ZOOM_IN)
                    update_bounds(bounds)
                    replot(fb1, buffer1, form.inp_list()["inp_0"], bounds, cursor, cache_buffer)

                elif inp_breaker == "-":
                    bounds = apply_zoom(bounds, ZOOM_OUT)
                    update_bounds(bounds)
                    replot(fb1, buffer1, form.inp_list()["inp_0"], bounds, cursor, cache_buffer)

                elif inp_breaker == "nav_u":
                    if not cursor.active:
                        bounds = apply_pan(bounds, 'up')
                        update_bounds(bounds)
                        replot(fb1, buffer1, form.inp_list()["inp_0"], bounds, cursor, cache_buffer)

                elif inp_breaker == "nav_d":
                    if not cursor.active:
                        bounds = apply_pan(bounds, 'down')
                        update_bounds(bounds)
                        replot(fb1, buffer1, form.inp_list()["inp_0"], bounds, cursor, cache_buffer)

                elif inp_breaker == "nav_l":
                    if cursor.active:
                        if cursor.x_pixel > 0:
                            cursor.x_pixel -= 1
                            update_cursor_only(fb1, buffer1, cache_buffer, cursor, bounds, form.inp_list()["inp_0"])
                    else:
                        bounds = apply_pan(bounds, 'left')
                        update_bounds(bounds)
                        replot(fb1, buffer1, form.inp_list()["inp_0"], bounds, cursor, cache_buffer)

                elif inp_breaker == "nav_r":
                    if cursor.active:
                        if cursor.x_pixel < 127:
                            cursor.x_pixel += 1
                            update_cursor_only(fb1, buffer1, cache_buffer, cursor, bounds, form.inp_list()["inp_0"])
                    else:
                        bounds = apply_pan(bounds, 'right')
                        update_bounds(bounds)
                        replot(fb1, buffer1, form.inp_list()["inp_0"], bounds, cursor, cache_buffer)

                elif inp_breaker in ("alpha", "beta"):
                    keypad_state_manager(x=inp_breaker)

                elif inp_breaker == "back":
                    break

                elif inp_breaker == "home":
                    del buffer1, fb1, cursor, cache_buffer
                    gc.collect()
                    current_app[0] = "home"
                    current_app[1] = "root"
                    return

            fb1.fill(0)
            form.refresh_rows = (0, form.actual_rows)
            display.clear_display()
            form_refresh.refresh()

        elif inp == "alpha" or inp == "beta":
            keypad_state_manager(x=inp)
            form.update_buffer("")
        elif inp not in ["alpha", "beta", "ok"]:
            form.update_buffer(inp)

        form_refresh.refresh(state=nav.current_state())

    print("Graph end, mem:", gc.mem_free())

def polynom1(exp, x):
    """Evaluate expression at x."""
    global eval_globals
    eval_globals["x"] = x
    y = eval(exp, eval_globals)
    return y