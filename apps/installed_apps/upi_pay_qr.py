import st7565 as st7565_display

try:
    import tools
    if hasattr(st7565_display, "graphics") and not hasattr(st7565_display.graphics, "pixels_changed"):
        st7565_display.graphics = tools.refresh(st7565_display.graphics, pixels_changed=200)
except Exception:
    pass

# Copyright (c) 2025 CalSci
# Licensed under the MIT License.

import framebuf  # type: ignore

import _thread
import utime as time  # type: ignore

from data_modules.object_handler import (
    app,
    display,
    form,
    form_refresh,
    keypad_state_manager,
    keypad_state_manager_reset,
    nav,
    typer,
)

PAYEE_NAME = "Rupesh Verma"
PAYEE_UPI_ID = "7007793564@ybl"

DISPLAY_WIDTH = 128
DISPLAY_HEIGHT = 64
DISPLAY_PAGES = DISPLAY_HEIGHT // 8
FB_SIZE = (DISPLAY_WIDTH * DISPLAY_HEIGHT) // 8

QR_VERSION = 3
QR_SIZE = 17 + (QR_VERSION * 4)
QR_DATA_CODEWORDS = 55
QR_ECC_CODEWORDS = 15
QR_MAX_PAYLOAD_LEN = 53
QR_FIXED_MASK = 0
QR_SCALE = 2
QR_RENDER_SIZE = QR_SIZE * QR_SCALE
QR_X = (DISPLAY_WIDTH - QR_RENDER_SIZE) // 2
QR_Y = (DISPLAY_HEIGHT - QR_RENDER_SIZE) // 2

_QR_RS_DIVISOR = None
_QR_FUNCTION_TEMPLATE = None
_QR_FUNCTION_MAP = None


def _go_back_to_installed_apps():
    keypad_state_manager_reset()
    app.set_app_name("installed_apps")
    app.set_group_name("root")


def _set_form_screen(amount_value=" ", status="OK: show QR"):
    if amount_value is None:
        amount_value = " "
    amount_value = str(amount_value)
    if amount_value == "":
        amount_value = " "
    if not amount_value.endswith(" "):
        amount_value += " "

    form.input_list = {"inp_0": amount_value}
    form.form_list = [
        "UPI Pay QR",
        PAYEE_NAME,
        PAYEE_UPI_ID,
        "Amount INR",
        "inp_0",
        status,
        "Back: exit",
    ]
    form.update()
    form.menu_cursor = 4
    form.display_cursor = 4
    form.refresh_rows = (0, form.actual_rows)
    form.input_cursor = len(amount_value.rstrip())
    form.input_display_position = 0


def _amount_to_paise(amount_text):
    amount_text = str(amount_text).strip()
    if not amount_text:
        raise ValueError("Enter amount")

    if amount_text.count(".") > 1:
        raise ValueError("Only one decimal")

    for ch in amount_text:
        if ch not in "0123456789.":
            raise ValueError("Use digits only")

    if "." in amount_text:
        whole, frac = amount_text.split(".", 1)
    else:
        whole, frac = amount_text, ""

    if whole == "":
        whole = "0"
    if frac == "":
        frac = "00"
    elif len(frac) == 1:
        frac += "0"
    elif len(frac) > 2:
        raise ValueError("Max 2 decimals")

    paise = (int(whole) * 100) + int(frac)
    if paise <= 0:
        raise ValueError("Amount > 0")
    return paise


def _paise_to_amount_string(paise):
    rupees = paise // 100
    frac = paise % 100
    if frac == 0:
        return str(rupees)
    if frac % 10 == 0:
        return str(rupees) + "." + str(frac // 10)
    return str(rupees) + "." + str(frac).rjust(2, "0")


def _build_upi_uri(amount_text):
    amount_text = str(amount_text)

    # Keep the payee name compact when needed so the QR still fits
    # on the 128x64 LCD at a 2-pixel module size.
    name_candidates = ("Rupesh", "RV", "")
    for payee_name in name_candidates:
        if payee_name:
            uri = (
                "upi://pay?pa="
                + PAYEE_UPI_ID
                + "&pn="
                + payee_name
                + "&am="
                + amount_text
                + "&cu=INR"
            )
        else:
            uri = "upi://pay?pa=" + PAYEE_UPI_ID + "&am=" + amount_text + "&cu=INR"
        if len(uri) <= QR_MAX_PAYLOAD_LEN:
            return uri
    raise ValueError("Amount too long")


def _gf_mul(x, y):
    result = 0
    while y:
        if y & 1:
            result ^= x
        y >>= 1
        x <<= 1
        if x & 0x100:
            x ^= 0x11D
    return result


def _reed_solomon_divisor(degree):
    result = [0] * (degree - 1) + [1]
    root = 1
    for _ in range(degree):
        for i in range(degree):
            result[i] = _gf_mul(result[i], root)
            if i + 1 < degree:
                result[i] ^= result[i + 1]
        root = _gf_mul(root, 0x02)
    return result


def _reed_solomon_remainder(data, divisor):
    result = [0] * len(divisor)
    for value in data:
        factor = value ^ result[0]
        for i in range(len(result) - 1):
            result[i] = result[i + 1] ^ _gf_mul(divisor[i], factor)
        result[-1] = _gf_mul(divisor[-1], factor)
    return result


def _get_rs_divisor():
    global _QR_RS_DIVISOR
    if _QR_RS_DIVISOR is None:
        _QR_RS_DIVISOR = _reed_solomon_divisor(QR_ECC_CODEWORDS)
    return _QR_RS_DIVISOR


def _sleep_ms(duration_ms):
    if hasattr(time, "sleep_ms"):
        time.sleep_ms(duration_ms)
    else:
        time.sleep(duration_ms / 1000)


def _append_bits(bits, value, bit_count):
    for shift in range(bit_count - 1, -1, -1):
        bits.append((value >> shift) & 1)


def _make_data_codewords(payload_text):
    payload_bytes = payload_text.encode("utf-8")
    if len(payload_bytes) > QR_MAX_PAYLOAD_LEN:
        raise ValueError("Payload too long")

    bits = []
    _append_bits(bits, 0x4, 4)  # Byte mode
    _append_bits(bits, len(payload_bytes), 8)
    for value in payload_bytes:
        _append_bits(bits, value, 8)

    capacity_bits = QR_DATA_CODEWORDS * 8
    terminator = capacity_bits - len(bits)
    if terminator > 4:
        terminator = 4
    _append_bits(bits, 0, terminator)

    while len(bits) % 8 != 0:
        bits.append(0)

    data = []
    for start in range(0, len(bits), 8):
        byte = 0
        for bit in bits[start : start + 8]:
            byte = (byte << 1) | bit
        data.append(byte)

    pad_bytes = (0xEC, 0x11)
    pad_index = 0
    while len(data) < QR_DATA_CODEWORDS:
        data.append(pad_bytes[pad_index])
        pad_index ^= 1
    return data


def _blank_matrix(size):
    return [[False] * size for _ in range(size)]


def _blank_function_map(size):
    return [[False] * size for _ in range(size)]


def _set_function_module(modules, function_map, x, y, is_black):
    if 0 <= x < QR_SIZE and 0 <= y < QR_SIZE:
        modules[y][x] = bool(is_black)
        function_map[y][x] = True


def _draw_finder(modules, function_map, x, y):
    for dy in range(-1, 8):
        for dx in range(-1, 8):
            xx = x + dx
            yy = y + dy
            if not (0 <= xx < QR_SIZE and 0 <= yy < QR_SIZE):
                continue
            if 0 <= dx <= 6 and 0 <= dy <= 6 and (
                dx in (0, 6) or dy in (0, 6) or (2 <= dx <= 4 and 2 <= dy <= 4)
            ):
                _set_function_module(modules, function_map, xx, yy, True)
            else:
                _set_function_module(modules, function_map, xx, yy, False)


def _draw_alignment(modules, function_map, cx, cy):
    for dy in range(-2, 3):
        for dx in range(-2, 3):
            _set_function_module(
                modules,
                function_map,
                cx + dx,
                cy + dy,
                max(abs(dx), abs(dy)) != 1,
            )


def _draw_function_patterns(modules, function_map):
    _draw_finder(modules, function_map, 0, 0)
    _draw_finder(modules, function_map, QR_SIZE - 7, 0)
    _draw_finder(modules, function_map, 0, QR_SIZE - 7)

    for i in range(8, QR_SIZE - 8):
        bit = (i % 2) == 0
        _set_function_module(modules, function_map, 6, i, bit)
        _set_function_module(modules, function_map, i, 6, bit)

    _draw_alignment(modules, function_map, 22, 22)

    for i in range(9):
        if i != 6:
            _set_function_module(modules, function_map, 8, i, False)
            _set_function_module(modules, function_map, i, 8, False)

    for i in range(8):
        _set_function_module(modules, function_map, QR_SIZE - 1 - i, 8, False)
        _set_function_module(modules, function_map, 8, QR_SIZE - 1 - i, False)

    _set_function_module(modules, function_map, 8, QR_SIZE - 8, True)


def _get_function_templates():
    global _QR_FUNCTION_TEMPLATE, _QR_FUNCTION_MAP
    if _QR_FUNCTION_TEMPLATE is None or _QR_FUNCTION_MAP is None:
        modules = _blank_matrix(QR_SIZE)
        function_map = _blank_function_map(QR_SIZE)
        _draw_function_patterns(modules, function_map)
        _QR_FUNCTION_TEMPLATE = modules
        _QR_FUNCTION_MAP = function_map
    return _copy_matrix(_QR_FUNCTION_TEMPLATE), _QR_FUNCTION_MAP


def _draw_codewords(modules, function_map, all_codewords):
    bits = []
    for value in all_codewords:
        _append_bits(bits, value, 8)

    bit_index = 0
    x = QR_SIZE - 1
    upward = True
    while x > 0:
        if x == 6:
            x -= 1
        y_range = range(QR_SIZE - 1, -1, -1) if upward else range(QR_SIZE)
        for y in y_range:
            for dx in (0, -1):
                xx = x + dx
                if not function_map[y][xx]:
                    modules[y][xx] = bit_index < len(bits) and bits[bit_index] == 1
                    bit_index += 1
        upward = not upward
        x -= 2


def _mask_bit(mask, x, y):
    if mask == 0:
        return ((x + y) % 2) == 0
    if mask == 1:
        return (y % 2) == 0
    if mask == 2:
        return (x % 3) == 0
    if mask == 3:
        return ((x + y) % 3) == 0
    if mask == 4:
        return (((y // 2) + (x // 3)) % 2) == 0
    if mask == 5:
        return (((x * y) % 2) + ((x * y) % 3)) == 0
    if mask == 6:
        return ((((x * y) % 2) + ((x * y) % 3)) % 2) == 0
    return ((((x + y) % 2) + ((x * y) % 3)) % 2) == 0


def _apply_mask(modules, function_map, mask):
    for y in range(QR_SIZE):
        for x in range(QR_SIZE):
            if not function_map[y][x] and _mask_bit(mask, x, y):
                modules[y][x] = not modules[y][x]


def _format_bits(mask):
    data = (0x01 << 3) | mask
    rem = data << 10
    generator = 0x537
    for shift in range(14, 9, -1):
        if (rem >> shift) & 1:
            rem ^= generator << (shift - 10)
    return ((data << 10) | rem) ^ 0x5412


def _draw_format_bits(modules, function_map, mask):
    bits = _format_bits(mask)

    for i in range(6):
        _set_function_module(modules, function_map, 8, i, ((bits >> i) & 1) != 0)
    _set_function_module(modules, function_map, 8, 7, ((bits >> 6) & 1) != 0)
    _set_function_module(modules, function_map, 8, 8, ((bits >> 7) & 1) != 0)
    _set_function_module(modules, function_map, 7, 8, ((bits >> 8) & 1) != 0)
    for i in range(9, 15):
        _set_function_module(modules, function_map, 14 - i, 8, ((bits >> i) & 1) != 0)

    for i in range(8):
        _set_function_module(
            modules,
            function_map,
            QR_SIZE - 1 - i,
            8,
            ((bits >> i) & 1) != 0,
        )
    for i in range(8, 15):
        _set_function_module(
            modules,
            function_map,
            8,
            QR_SIZE - 15 + i,
            ((bits >> i) & 1) != 0,
        )

    _set_function_module(modules, function_map, 8, QR_SIZE - 8, True)


def _copy_matrix(matrix):
    return [row[:] for row in matrix]


def _penalty_score(modules):
    score = 0

    for y in range(QR_SIZE):
        run_color = modules[y][0]
        run_length = 1
        for x in range(1, QR_SIZE):
            if modules[y][x] == run_color:
                run_length += 1
            else:
                if run_length >= 5:
                    score += 3 + (run_length - 5)
                run_color = modules[y][x]
                run_length = 1
        if run_length >= 5:
            score += 3 + (run_length - 5)

    for x in range(QR_SIZE):
        run_color = modules[0][x]
        run_length = 1
        for y in range(1, QR_SIZE):
            if modules[y][x] == run_color:
                run_length += 1
            else:
                if run_length >= 5:
                    score += 3 + (run_length - 5)
                run_color = modules[y][x]
                run_length = 1
        if run_length >= 5:
            score += 3 + (run_length - 5)

    for y in range(QR_SIZE - 1):
        for x in range(QR_SIZE - 1):
            color = modules[y][x]
            if (
                modules[y][x + 1] == color
                and modules[y + 1][x] == color
                and modules[y + 1][x + 1] == color
            ):
                score += 3

    pattern1 = [True, False, True, True, True, False, True, False, False, False, False]
    pattern2 = [False, False, False, False, True, False, True, True, True, False, True]
    for y in range(QR_SIZE):
        for x in range(QR_SIZE - 10):
            row = modules[y][x : x + 11]
            if row == pattern1 or row == pattern2:
                score += 40
    for x in range(QR_SIZE):
        for y in range(QR_SIZE - 10):
            col = [modules[y + step][x] for step in range(11)]
            if col == pattern1 or col == pattern2:
                score += 40

    dark_count = 0
    for row in modules:
        for value in row:
            if value:
                dark_count += 1
    total = QR_SIZE * QR_SIZE
    score += (abs((dark_count * 20) - (total * 10)) // total) * 10
    return score


def _make_qr_matrix(payload_text):
    data_codewords = _make_data_codewords(payload_text)
    divisor = _get_rs_divisor()
    ecc_codewords = _reed_solomon_remainder(data_codewords, divisor)

    modules, function_map = _get_function_templates()
    _draw_codewords(modules, function_map, data_codewords + ecc_codewords)

    # A fixed mask is much faster on MicroPython than evaluating all 8 masks.
    # It does not change correctness; it only skips the quality search step.
    _apply_mask(modules, function_map, QR_FIXED_MASK)
    _draw_format_bits(modules, function_map, QR_FIXED_MASK)
    return modules


def _draw_qr(fb, matrix, x0, y0, scale):
    for y in range(QR_SIZE):
        for x in range(QR_SIZE):
            if matrix[y][x]:
                fb.fill_rect(x0 + (x * scale), y0 + (y * scale), scale, scale, 1)


def _draw_centered_text(fb, text_value, y):
    x = (DISPLAY_WIDTH - (len(text_value) * 8)) // 2
    if x < 0:
        x = 0
    fb.text(text_value, x, y, 1)


def _show_loading_screen(frame_no=0):
    buffer = bytearray(FB_SIZE)
    fb = framebuf.FrameBuffer(buffer, DISPLAY_WIDTH, DISPLAY_HEIGHT, framebuf.MONO_VLSB)
    fb.fill(0)
    dots = "." * (frame_no % 4)
    _draw_centered_text(fb, "Generating", 20)
    _draw_centered_text(fb, "QR" + dots, 32)
    display.clear_display()
    display.graphics(buffer, page=0, column=0, width=DISPLAY_WIDTH, pages=DISPLAY_PAGES)


def _set_qr_job_value(job, key, value):
    lock = job["lock"]
    lock.acquire()
    try:
        job[key] = value
    finally:
        lock.release()


def _get_qr_job_snapshot(job):
    lock = job["lock"]
    lock.acquire()
    try:
        return job["done"], job["matrix"], job["error"]
    finally:
        lock.release()


def _qr_worker(amount_text, job):
    try:
        payload = _build_upi_uri(amount_text)
        matrix = _make_qr_matrix(payload)
        _set_qr_job_value(job, "matrix", matrix)
    except Exception as exc:
        _set_qr_job_value(job, "error", str(exc))
    _set_qr_job_value(job, "done", True)


def _build_qr_matrix_with_loading(amount_text):
    job = {
        "lock": _thread.allocate_lock(),
        "done": False,
        "matrix": None,
        "error": None,
    }

    try:
        _thread.start_new_thread(_qr_worker, (amount_text, job))
    except Exception:
        payload = _build_upi_uri(amount_text)
        return _make_qr_matrix(payload), None

    frame_no = 0
    while True:
        done, matrix, error = _get_qr_job_snapshot(job)
        if done:
            return matrix, error
        _show_loading_screen(frame_no)
        frame_no += 1
        _sleep_ms(120)


def _show_qr_screen(matrix):
    buffer = bytearray(FB_SIZE)
    fb = framebuf.FrameBuffer(buffer, DISPLAY_WIDTH, DISPLAY_HEIGHT, framebuf.MONO_VLSB)
    fb.fill(0)
    _draw_qr(fb, matrix, QR_X, QR_Y, QR_SCALE)
    display.clear_display()
    display.graphics(buffer, page=0, column=0, width=DISPLAY_WIDTH, pages=DISPLAY_PAGES)


def upi_pay_qr(db={}):
    keypad_state_manager_reset()

    current_amount = " "
    status = "OK: show QR"
    _set_form_screen(current_amount, status)
    display.clear_display()
    form_refresh.refresh(state=nav.current_state())

    mode = "form"

    while True:
        inp = typer.start_typing()

        if inp == "off":
            _go_back_to_installed_apps()
            break

        if inp == "alpha" or inp == "beta":
            keypad_state_manager(x=inp)
            if mode == "form":
                form.update_buffer("")
                form_refresh.refresh(state=nav.current_state())
            continue

        if mode == "form":
            if inp == "back":
                _go_back_to_installed_apps()
                break

            if inp == "ok":
                raw_amount = form.inp_list().get("inp_0", " ")
                try:
                    paise = _amount_to_paise(raw_amount)
                    current_amount = _paise_to_amount_string(paise)
                    matrix, error = _build_qr_matrix_with_loading(current_amount)
                    if error:
                        raise ValueError(error)
                    _show_qr_screen(matrix)
                    mode = "qr"
                    continue
                except Exception as exc:
                    current_amount = raw_amount.strip() or " "
                    status = str(exc)
                    _set_form_screen(current_amount, status)
                    display.clear_display()
                    form_refresh.refresh(state=nav.current_state())
                    continue

            form.update_buffer(inp)
            status = "OK: show QR"
            current_amount = form.inp_list().get("inp_0", " ").strip() or " "
            form.form_list[5] = status
            form.refresh_rows = (0, form.actual_rows)
            form_refresh.refresh(state=nav.current_state())

        else:
            if inp == "back" or inp == "ok":
                keypad_state_manager_reset()
                status = "OK: show QR"
                _set_form_screen(current_amount, status)
                display.clear_display()
                form_refresh.refresh(state=nav.current_state())
                mode = "form"
