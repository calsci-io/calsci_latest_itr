import st7565 as display

try:
    import tools

    if hasattr(display, "graphics") and not hasattr(display.graphics, "pixels_changed"):
        display.graphics = tools.refresh(display.graphics, pixels_changed=200)
except Exception:
    pass

# Copyright (c) 2025 CalSci
# Licensed under the MIT License.

try:
    import machine  # type: ignore
except ImportError:
    from mocking import machine  # type: ignore

from apps.installed_apps._mono_ui import MonoCanvas, clip_text_px
from data_modules.object_handler import (
    app,
    display,
    form,
    form_refresh,
    keypad_state_manager,
    keypad_state_manager_reset,
    menu,
    menu_refresh,
    nav,
    typer,
)
from process_modules import boot_up_data_update
from process_modules.pc_folder_sync import (
    DEFAULT_PORT,
    SyncError,
    load_settings,
    save_settings,
    sync_folder,
)


def _format_form_value(value, fallback=""):
    value = str(value if value not in (None, "") else fallback).strip()
    return (value + " ") if value else " "


def _format_bytes(size_value):
    try:
        size_value = int(size_value)
    except Exception:
        size_value = 0
    units = ("B", "KB", "MB")
    unit_index = 0
    value = float(size_value)
    while value >= 1024.0 and unit_index < len(units) - 1:
        value /= 1024.0
        unit_index += 1
    if unit_index == 0:
        return "{} {}".format(int(value), units[unit_index])
    return "{:.1f} {}".format(value, units[unit_index])


class _SyncDashboard:
    def __init__(self):
        self.canvas = MonoCanvas()

    def render(self, snapshot):
        folder_name = str(snapshot.get("folder_name", "") or "-")
        file_index = int(snapshot.get("file_index", 0) or 0)
        file_count = int(snapshot.get("file_count", 0) or 0)
        bytes_done = int(snapshot.get("bytes_done", 0) or 0)
        bytes_total = int(snapshot.get("bytes_total", 0) or 0)
        current_file = str(snapshot.get("current_file", "") or "-")
        message = str(snapshot.get("message", "") or "Working")

        percent = 0
        if bytes_total > 0:
            percent = int((bytes_done * 100) / max(1, bytes_total))
        elif file_count > 0:
            percent = int((file_index * 100) / max(1, file_count))
        if percent < 0:
            percent = 0
        if percent > 100:
            percent = 100

        self.canvas.clear()
        self.canvas.fill_rect(0, 0, 128, 10, 1)
        self.canvas.draw_text("PC Folder Sync", 2, 1, color=0)
        self.canvas.draw_text_in_rect("{}%".format(percent), 92, 1, 34, 8, color=0, align="right")

        self.canvas.draw_text("Folder:", 2, 14, color=1)
        self.canvas.draw_text(clip_text_px(folder_name, 82), 38, 14, color=1, max_width=88)
        self.canvas.draw_text("Files:", 2, 23, color=1)
        self.canvas.draw_text("{}/{}".format(file_index, file_count), 38, 23, color=1, max_width=88)
        self.canvas.draw_text(clip_text_px(current_file, 124), 2, 32, color=1, max_width=124)
        self.canvas.draw_text(message, 2, 41, color=1, max_width=124)
        self.canvas.draw_text(
            "{}/{}".format(_format_bytes(bytes_done), _format_bytes(bytes_total)),
            2,
            50,
            color=1,
            max_width=124,
        )

        self.canvas.rect(10, 58, 108, 5, 1)
        fill_width = int(((percent / 100.0) * 106))
        if fill_width > 0:
            self.canvas.fill_rect(11, 59, fill_width, 3, 1)
        self.canvas.flush()


def _show_menu_screen(lines):
    menu.menu_list = list(lines)
    menu.update()
    display.clear_display()
    menu_refresh.refresh()

    while True:
        inp = typer.start_typing()

        if inp in ("back", "ok"):
            return

        if inp == "alpha" or inp == "beta":
            keypad_state_manager(x=inp)
            menu.update_buffer("")
        elif inp == "caps":
            keypad_state_manager(x="A")
            menu.update_buffer("")
        elif inp == "off":
            boot_up_data_update.main()
            machine.deepsleep()

        menu.update_buffer(inp)
        menu_refresh.refresh(state=nav.current_state())


def _collect_inputs():
    saved = load_settings()
    form.input_list = {
        "inp_0": _format_form_value(saved.get("host", "")),
        "inp_1": _format_form_value(saved.get("port", DEFAULT_PORT), str(DEFAULT_PORT)),
        "inp_2": _format_form_value(saved.get("folder_name", "")),
    }
    form.form_list = [
        "PC IP:",
        "inp_0",
        "Port:",
        "inp_1",
        "Folder name:",
        "inp_2",
        "Leave blank for the PC default",
    ]
    form.update()
    display.clear_display()
    form_refresh.refresh()

    while True:
        inp = typer.start_typing()
        if inp == "back":
            return None
        if inp == "ok":
            host = str(form.input_list["inp_0"]).strip()
            port = str(form.input_list["inp_1"]).strip() or str(DEFAULT_PORT)
            folder_name = str(form.input_list["inp_2"]).strip()
            return {"host": host, "port": port, "folder_name": folder_name}

        if inp == "alpha" or inp == "beta":
            keypad_state_manager(x=inp)
            form.update_buffer("")
        elif inp == "caps":
            keypad_state_manager(x="A")
            form.update_buffer("")
        elif inp == "off":
            boot_up_data_update.main()
            machine.deepsleep()
        else:
            form.update_buffer(inp)

        form_refresh.refresh(state=nav.current_state())


def pc_folder_sync():
    keypad_state_manager_reset()
    dashboard = _SyncDashboard()

    while True:
        inputs = _collect_inputs()
        if inputs is None:
            app.set_app_name("installed_apps")
            app.set_group_name("root")
            return

        host = inputs["host"]
        port = inputs["port"]
        folder_name = inputs["folder_name"]

        try:
            save_settings(host=host, port=port, folder_name=folder_name)
            summary = sync_folder(
                host=host,
                port=port,
                folder_name=folder_name,
                progress_cb=dashboard.render,
            )
            if folder_name:
                save_settings(host=host, port=port, folder_name=folder_name)
            else:
                save_settings(host=host, port=port, folder_name="")

            result_lines = [
                "PC Folder Sync",
                "Download complete",
                "Folder: {}".format(summary["folder_name"]),
                "Files: {}".format(summary["file_count"]),
                "Bytes: {}".format(_format_bytes(summary["total_bytes"])),
            ]
            if summary["installed_apps"]:
                result_lines.append("Apps updated:")
                result_lines.append(", ".join(summary["installed_apps"])[:20])
            else:
                result_lines.append("No installed app DB changes")
            result_lines.append("Press OK to exit")
            _show_menu_screen(result_lines)
            app.set_app_name("installed_apps")
            app.set_group_name("root")
            return
        except SyncError as err:
            _show_menu_screen(
                [
                    "PC Folder Sync",
                    "Download failed",
                    clip_text_px(str(err), 120),
                    "",
                    "Fix IP/port/folder",
                    "Press OK to retry",
                ]
            )
