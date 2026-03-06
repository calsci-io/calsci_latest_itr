import st7565 as display

try:
    import tools
    if hasattr(display, "graphics") and not hasattr(display.graphics, "pixels_changed"):
        display.graphics = tools.refresh(display.graphics, pixels_changed=200)
except Exception:
    pass

# Copyright (c) 2025 CalSci
# Licensed under the MIT License.

import utime as time  # type:ignore
from urandom import getrandbits  # type:ignore
try:
    import ujson as json  # type:ignore
except Exception:
    import json  # type:ignore

try:
    import urequests as requests  # type:ignore
except Exception:
    import requests  # type:ignore

try:
    import network  # type:ignore
except Exception:
    network = None

from data_modules.object_handler import (
    app,
    current_app,
    data_bucket,
    display,
    form,
    form_refresh,
    keypad_state_manager,
    nav,
    text,
    text_refresh,
    typer,
)

ENV_PATHS = (".env", "/.env")
OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
SYSTEM_PROMPT_50_WORDS = "Always answer in 50 words or fewer. Never exceed 50 words."


NOISE_CHARS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
TEXT_COLS = 21


def _line21(s):
    s = str(s)
    if len(s) > TEXT_COLS:
        return s[:TEXT_COLS]
    return s.center(TEXT_COLS)


def _render_text_lines(lines, state="ChatGPT"):
    text.all_clear()
    text.update_buffer("".join(_line21(line) for line in lines))
    text_refresh.new = True
    text_refresh.refresh(state=state)


def _load_env(paths=ENV_PATHS):
    env = {}
    for path in paths:
        try:
            with open(path, "r") as env_file:
                for raw_line in env_file:
                    line = raw_line.strip()
                    if (not line) or line.startswith("#") or ("=" not in line):
                        continue
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()
                    if value and (value[0] == value[-1]) and value[0] in ("'", '"'):
                        value = value[1:-1]
                    env[key] = value
        except OSError:
            continue
    return env


def _is_wifi_connected():
    if network is None:
        return True
    try:
        sta_if = network.WLAN(network.STA_IF)
        return sta_if.isconnected()
    except Exception:
        return data_bucket.get("connection_status_g", False)


def _truncate_to_words(message, max_words=50):
    words = str(message).strip().split()
    if len(words) <= max_words:
        return " ".join(words)
    return " ".join(words[:max_words])


def _extract_response_text(payload):
    output_text = payload.get("output_text", "")
    if isinstance(output_text, str) and output_text.strip():
        return output_text

    parts = []
    for item in payload.get("output", []):
        if not isinstance(item, dict):
            continue
        if item.get("type") != "message":
            continue
        for block in item.get("content", []):
            if not isinstance(block, dict):
                continue
            if block.get("type") in ("output_text", "text"):
                parts.append(block.get("text", ""))
    return "".join(parts)


def _call_openai(prompt):
    if not _is_wifi_connected():
        print("[ChatGPT] Wi-Fi not connected")
        return "No Wi-Fi. Connect from Settings."

    env = _load_env()
    api_key = env.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        print("[ChatGPT] OPENAI_API_KEY missing in .env")
        return "Set OPENAI_API_KEY in .env"

    model = env.get("OPENAI_MODEL", "gpt-5.4").strip() or "gpt-5.4"

    payload = {
        "model": model,
        "instructions": SYSTEM_PROMPT_50_WORDS,
        "input": prompt,
        "temperature": 0.7,
        "max_output_tokens": 120,
    }
    headers = {
        "Authorization": "Bearer " + api_key,
        "Content-Type": "application/json",
    }

    response = None
    try:
        try:
            response = requests.post(
                OPENAI_RESPONSES_URL,
                data=json.dumps(payload),
                headers=headers,
                timeout=45,
            )
        except TypeError:
            response = requests.post(
                OPENAI_RESPONSES_URL,
                data=json.dumps(payload),
                headers=headers,
            )

        status_code = getattr(response, "status_code", 0)
        print("[ChatGPT] OpenAI status:", status_code)
        if status_code and status_code >= 400:
            error_msg = ""
            try:
                err = response.json().get("error", {})
                if isinstance(err, dict):
                    error_msg = err.get("message", "")
            except Exception:
                pass
            if error_msg:
                print("[ChatGPT] API error:", error_msg)
                return "API error: " + error_msg
            return "API error: " + str(status_code)

        body = response.json()
        error_info = body.get("error")
        if isinstance(error_info, dict):
            return "API error: " + error_info.get("message", "unknown")

        reply = _extract_response_text(body).strip()
        if not reply:
            print("[ChatGPT] Empty API response payload:", body)
            return "No response from API."

        return _truncate_to_words(reply, 50)
    except Exception as err:
        print("[ChatGPT] Request failed:", err)
        return "Request failed: " + str(err)
    finally:
        try:
            if response is not None:
                response.close()
        except Exception:
            pass

chatgpt_logo_128x64 = bytearray(b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x80\xe0\xf0\xf8\xf8\x7c\x7c\x3e\x1e\x1f\x1f\x0f\x0f\x0f\x0f\x0f\x1f\x1f\x1e\x3e\xbc\xfc\xf8\xf8\xf0\xe0\xe0\xe0\xe0\xe0\xe0\xe0\xe0\xc0\xc0\xc0\x80\x80\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x80\xc0\xe0\xe0\xf0\xf0\xf0\xf8\xfc\xff\xff\xff\x07\x03\x00\x00\x00\x80\xc0\xc0\xe0\xe0\xf0\xf8\xf8\x7c\x7c\x3e\x1e\x1f\x0f\x0f\x07\x07\x03\x03\x83\x01\x01\x01\x01\x01\x03\x03\x03\x07\x0f\x1f\x3f\x7e\xfc\xf8\xf0\xe0\x80\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x80\xf0\xfc\xfe\xff\x3f\x0f\x07\x03\x01\x01\x00\xff\xff\xff\xff\x00\x00\x00\x00\x00\x00\xff\xff\xff\x03\x01\x81\x80\xc0\xe0\xe0\xf0\xf0\xf8\xf8\x9c\x1c\x0e\x0f\x07\x0f\x0f\x1f\x1e\x3e\x7c\x7c\xf8\xf8\xf0\xe0\xe0\xc0\xc0\x81\xff\xff\xff\xff\x78\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x7f\xff\xff\xff\xe1\x00\x00\x00\x00\x00\x00\x00\xff\xff\xff\xff\xc0\x00\x00\x00\x00\x00\xff\xff\xff\x0f\x07\x07\x03\x01\x01\x00\x00\x01\x01\x03\x07\x07\x0f\xfe\xfe\xfc\x38\x78\x70\xf0\xe0\xe0\xc0\x80\x81\x01\x03\x07\x07\x0f\x1f\x3f\xff\xff\xf8\xf0\xc0\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x03\x0f\x1f\xff\xff\xfc\xf8\xf0\xe0\xe0\xc0\x80\x81\x01\x03\x07\x07\x0f\x0e\x1e\x1c\x3f\x7f\x7f\xf0\xe0\xe0\xc0\x80\x80\x00\x00\x80\x80\xc0\xe0\xe0\xf0\xff\xff\xff\x00\x00\x00\x00\x00\x03\xff\xff\xff\xff\x00\x00\x00\x00\x00\x00\x00\x87\xff\xff\xff\xfe\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x0e\xff\xff\xff\xff\x81\x03\x03\x07\x07\x0f\x1f\x1f\x3e\x3e\x7c\x78\xf8\xf0\xf0\xe0\xf0\x70\x78\x39\x1f\x1f\x0f\x0f\x07\x07\x03\x01\x81\x80\xc0\xff\xff\xff\x00\x00\x00\x00\x00\x00\xff\xff\xff\xff\x00\x80\x80\xc0\xe0\xf0\xfc\xff\x7f\x3f\x0f\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x07\x0f\x1f\x3f\x7e\xfc\xf8\xf0\xe0\xc0\xc0\xc0\xc0\x80\x80\x80\x80\xc1\xc0\xc0\xe0\xe0\xf0\xf0\xf8\x78\x7c\x3e\x3e\x1f\x1f\x0f\x07\x07\x03\x03\x01\x00\x00\x00\xc0\xe0\xff\xff\xff\x3f\x1f\x0f\x0f\x0f\x07\x07\x03\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x01\x03\x03\x03\x07\x07\x07\x07\x07\x07\x07\x07\x0f\x1f\x1f\x3f\x3d\x7c\x78\xf8\xf8\xf0\xf0\xf0\xf0\xf0\xf8\xf8\x78\x7c\x3e\x3e\x1f\x1f\x0f\x07\x03\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')


def _show_startup_logo():
    display.clear_display()
    display.graphics(chatgpt_logo_128x64)
    time.sleep_ms(1000)
    display.clear_display()


def _reset_prompt_form(prompt_value=" "):
    if prompt_value == "":
        prompt_value = " "
    form.input_list = {"inp_0": prompt_value}
    form.form_list = ["prompt:", "inp_0"]
    form.menu_cursor = 1
    form.input_cursor = len(prompt_value) if prompt_value != " " else 0
    form.input_display_position = 0
    form.update()


def _go_home():
    app.set_app_name("home")
    app.set_group_name("root")
    current_app[0] = "home"


def _rand_idx(limit):
    if limit <= 0:
        return 0
    return getrandbits(16) % limit


def _rand_ms(min_ms, max_ms):
    if max_ms <= min_ms:
        return min_ms
    return min_ms + (getrandbits(16) % (max_ms - min_ms + 1))


def _thinking_nav_animation_on_prompt(total_ms=1200, step_ms=150):
    # Runs on prompt screen navbar: Thinking. Thinking.. Thinking... Thinking..
    dots_seq = [".", "..", "...", ".."]
    frames = total_ms // step_ms
    for i in range(frames):
        form_refresh.refresh(state="             ")
        form_refresh.refresh(state="Thinking" + dots_seq[i % len(dots_seq)])
        time.sleep_ms(step_ms)


def _stream_fake_gpt(text_to_stream):
    # No separate thinking window; animate in navbar on prompt screen
    _thinking_nav_animation_on_prompt(total_ms=1200, step_ms=100)

    text.all_clear()
    text_refresh.new = True
    text_refresh.refresh(state=" > ChatGPT")

    for ch in text_to_stream:
        if ch in " ,.;" and _rand_idx(100) < 35:
            time.sleep_ms(_rand_ms(400, 600))

        if ch not in " \n" and _rand_idx(100) < 28:
            fake_ch = NOISE_CHARS[_rand_idx(len(NOISE_CHARS))]
            text.update_buffer(fake_ch)
            text_refresh.refresh(state="ChatGPT")
            time.sleep_ms(_rand_ms(20, 60))
            text.update_buffer("nav_b")

        text.update_buffer(ch)
        text_refresh.refresh(state="ChatGPT")
        time.sleep_ms(_rand_ms(18, 45))


def ChatGPT():
    display.clear_display()
    _show_startup_logo()

    _reset_prompt_form()
    form_refresh.refresh(state=nav.current_state())

    mode = "input"  # input | response
    last_prompt = " "

    while True:
        inp = typer.start_typing()

        if inp == "alpha" or inp == "beta":
            keypad_state_manager(x=inp)
            if mode == "input":
                form.update_buffer("")
                form_refresh.refresh(state=nav.current_state())
            else:
                text_refresh.refresh(state="ChatGPT")
            time.sleep(0.03)
            continue

        if mode == "input":
            if inp == "back":
                _go_home()
                break

            if inp == "ok":
                entered_prompt = form.inp_list().get("inp_0", " ").strip()
                if not entered_prompt:
                    _stream_fake_gpt("Please enter a prompt.")
                    mode = "response"
                    continue

                last_prompt = entered_prompt
                form_refresh.refresh(state="Thinking...")
                gpt_reply = _call_openai(entered_prompt)
                _stream_fake_gpt(gpt_reply)
                mode = "response"
                continue

            form.update_buffer(inp)
            form_refresh.refresh(state=nav.current_state())

        else:  # mode == "response"
            if inp == "back":
                display.clear_display()
                _reset_prompt_form(last_prompt)
                form_refresh.refresh(state=nav.current_state())
                mode = "input"
                continue

            if inp == "ok":
                display.clear_display()
                _reset_prompt_form(last_prompt)
                form_refresh.refresh(state=nav.current_state())
                mode = "input"
                continue

            if inp in ("nav_u", "nav_d", "nav_l", "nav_r", "nav_b"):
                text.update_buffer(inp)
                text_refresh.refresh(state="ChatGPT")

        time.sleep(0.03)
