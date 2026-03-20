import st7565 as display

# try:
#     import tools
#     if hasattr(display, "graphics") and not hasattr(display.graphics, "pixels_changed"):
#         display.graphics = tools.refresh(display.graphics, pixels_changed=200)
# except Exception:
#     pass

# Copyright (c) 2025 CalSci
# Licensed under the MIT License.

import gc
import network  # type: ignore
import utime as time  # type:ignore

try:
    import urequests as requests  # type: ignore
except Exception:
    import requests  # type: ignore

try:
    import ujson as json  # type: ignore
except Exception:
    import json

from data_modules.object_handler import (
    app,
    display,
    form,
    form_refresh,
    keypad_state_manager,
    nav,
    text,
    text_refresh,
    typer,
)

TEXT_COLS = 21
SEARCH_STATE = "Search"
MAX_RESULTS = 4
DUCKDUCKGO_URL = (
    "https://api.duckduckgo.com/?q={query}&format=json&no_redirect=1"
    "&no_html=1&skip_disambig=1"
)
WIKIPEDIA_URL = (
    "https://en.wikipedia.org/w/api.php?action=opensearch&search={query}"
    "&limit=4&namespace=0&format=json"
)


def _pad_line(value):
    value = str(value)
    if len(value) > TEXT_COLS:
        return value[:TEXT_COLS]
    return value.ljust(TEXT_COLS)


def _wrap_text(value):
    words = str(value).replace("\n", " ").split()
    if not words:
        return [""]

    lines = []
    current = ""
    for word in words:
        while len(word) > TEXT_COLS:
            if current:
                lines.append(current)
                current = ""
            lines.append(word[:TEXT_COLS])
            word = word[TEXT_COLS:]

        if not current:
            current = word
        elif len(current) + 1 + len(word) <= TEXT_COLS:
            current += " " + word
        else:
            lines.append(current)
            current = word

    if current:
        lines.append(current)
    return lines


def _render_text_lines(lines, state=SEARCH_STATE):
    wrapped = []
    for line in lines:
        if line == "":
            wrapped.append("")
            continue
        wrapped.extend(_wrap_text(line))

    if not wrapped:
        wrapped = ["No results"]

    text.all_clear()
    text.update_buffer("".join(_pad_line(line) for line in wrapped))
    text_refresh.new = True
    text_refresh.refresh(state=state)


def _reset_prompt_form(query_value=" "):
    if not query_value:
        query_value = " "
    form.input_list = {"inp_0": query_value}
    form.form_list = ["web search:", "inp_0"]
    form.update()
    form.menu_cursor = 1
    form.display_cursor = 1
    form.input_cursor = len(query_value) if query_value != " " else 0
    form.input_display_position = 0


def _go_home():
    app.set_app_name("home")
    app.set_group_name("root")


def _urlencode(value):
    encoded = []
    for byte in str(value).encode("utf-8"):
        if (
            48 <= byte <= 57
            or 65 <= byte <= 90
            or 97 <= byte <= 122
            or byte in b"-_.~"
        ):
            encoded.append(chr(byte))
        elif byte == 32:
            encoded.append("+")
        else:
            encoded.append("%{:02X}".format(byte))
    return "".join(encoded)


def _http_get_json(url):
    response = None
    try:
        try:
            response = requests.get(url, timeout=10)
        except TypeError:
            response = requests.get(url)

        status_code = getattr(response, "status_code", 200)
        if status_code != 200:
            return None, "HTTP {}".format(status_code)

        try:
            data = response.json()
        except Exception:
            data = json.loads(response.text)
        return data, None
    except Exception as exc:
        return None, str(exc)
    finally:
        if response is not None:
            try:
                response.close()
            except Exception:
                pass


def _flatten_duckduckgo_topics(items, results):
    for item in items:
        if not isinstance(item, dict):
            continue
        text_value = item.get("Text")
        if text_value:
            results.append(text_value)
        topics = item.get("Topics")
        if isinstance(topics, list):
            _flatten_duckduckgo_topics(topics, results)


def _search_duckduckgo(query):
    url = DUCKDUCKGO_URL.format(query=_urlencode(query))
    data, error = _http_get_json(url)
    if error:
        return None, error

    lines = ["Query: {}".format(query), "Source: DuckDuckGo", ""]
    found_content = False

    heading = data.get("Heading")
    abstract = data.get("AbstractText")
    if heading:
        lines.append("Top match: {}".format(heading))
        found_content = True
    if abstract:
        lines.append(abstract)
        found_content = True

    related = []
    results = data.get("Results")
    if isinstance(results, list):
        for item in results:
            if isinstance(item, dict) and item.get("Text"):
                related.append(item["Text"])
    topics = data.get("RelatedTopics")
    if isinstance(topics, list):
        _flatten_duckduckgo_topics(topics, related)

    unique_related = []
    for item in related:
        if item not in unique_related:
            unique_related.append(item)
        if len(unique_related) >= MAX_RESULTS:
            break

    if unique_related:
        if found_content:
            lines.append("")
        lines.append("More results:")
        for index, item in enumerate(unique_related, 1):
            lines.append("{}. {}".format(index, item))
        found_content = True

    if not found_content:
        return None, "No instant answer"
    return lines, None


def _search_wikipedia(query):
    url = WIKIPEDIA_URL.format(query=_urlencode(query))
    data, error = _http_get_json(url)
    if error:
        return None, error

    if not isinstance(data, list) or len(data) < 4:
        return None, "Invalid response"

    titles = data[1]
    descriptions = data[2]

    if not titles:
        return None, "No results"

    lines = ["Query: {}".format(query), "Source: Wikipedia", ""]
    for index, title in enumerate(titles[:MAX_RESULTS], 1):
        lines.append("{}. {}".format(index, title))
        if index - 1 < len(descriptions) and descriptions[index - 1]:
            lines.append(descriptions[index - 1])
        lines.append("")

    while lines and lines[-1] == "":
        lines.pop()
    return lines, None


def _build_search_result(query):
    if not query:
        return ["Enter a search query.", "Use OK to search."]

    sta_if = network.WLAN(network.STA_IF)
    if not sta_if.active() or not sta_if.isconnected():
        return [
            "WiFi is not connected.",
            "Open Settings.",
            "Use wifi_app first.",
        ]

    gc.collect()

    duck_lines, duck_error = _search_duckduckgo(query)
    if duck_lines:
        return duck_lines

    wiki_lines, wiki_error = _search_wikipedia(query)
    if wiki_lines:
        return wiki_lines

    error_lines = ["Search failed."]
    if duck_error:
        error_lines.append("DuckDuckGo: {}".format(duck_error))
    if wiki_error:
        error_lines.append("Wikipedia: {}".format(wiki_error))
    error_lines.append("Try a shorter query.")
    return error_lines


def ChatGPT():
    display.clear_display()
    _reset_prompt_form()
    form_refresh.refresh(state=nav.current_state())

    mode = "input"
    last_query = " "

    while True:
        inp = typer.start_typing()

        if inp in ("alpha", "beta"):
            keypad_state_manager(x=inp)
            if mode == "input":
                form.update_buffer("")
                form_refresh.refresh(state=nav.current_state())
            else:
                text_refresh.refresh(state=SEARCH_STATE)
            time.sleep(0.03)
            continue

        if mode == "input":
            if inp == "back":
                _go_home()
                break

            if inp == "ok":
                last_query = form.inp_list().get("inp_0", " ").strip() or " "
                _render_text_lines(
                    [
                        "Searching...",
                        last_query,
                    ]
                )
                result_lines = _build_search_result(last_query.strip())
                _render_text_lines(result_lines)
                mode = "response"
                continue

            form.update_buffer(inp)
            form_refresh.refresh(state=nav.current_state())
        else:
            if inp == "back":
                display.clear_display()
                _reset_prompt_form(last_query)
                form_refresh.refresh(state=nav.current_state())
                mode = "input"
                continue

            if inp == "ok":
                result_lines = _build_search_result(last_query.strip())
                _render_text_lines(result_lines)
                continue

            if inp in ("nav_u", "nav_d", "nav_l", "nav_r", "nav_b"):
                text.update_buffer(inp)
                text_refresh.refresh(state=SEARCH_STATE)

        time.sleep(0.03)
