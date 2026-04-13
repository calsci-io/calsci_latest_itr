from core.contracts import BaseApp
from ui.components import apply_text_edit, fields_from_pairs, menu_move
from ui.models import FormScreen, MenuScreen, TextScreen

from .common import clamp_scroll, go_back


class FunctionLockerApp(BaseApp):
    MENU_ITEMS = ["Open Vault", "Create New", "Delete Function"]

    def __init__(self, manifest):
        super().__init__(manifest)
        self.view = "menu"
        self.menu_index = 0
        self.create_selected = 0
        self.vault_scroll = 0
        self.delete_index = 0
        self.message = ""
        self.form = {
            "name": "",
            "variables": "",
            "expression": "",
        }

    def enter(self, ctx, params=None):
        self.view = "menu"
        self.message = ""
        self.mark_dirty()

    def _functions(self, ctx):
        items = list(ctx.storage.get_functions())
        items.sort(key=lambda item: item.get("name", "").lower())
        return items

    def _save(self, ctx):
        name = self.form["name"].strip()
        expression = self.form["expression"].strip()
        variables = [item.strip() for item in self.form["variables"].split(",") if item.strip()]
        if not name or not expression:
            self.message = "Name and expression required."
            self.mark_dirty()
            return
        ctx.storage.save_function(name, variables, expression)
        self.form = {"name": "", "variables": "", "expression": ""}
        self.create_selected = 0
        self.message = "Function saved."
        self.view = "menu"
        self.mark_dirty()

    def handle_event(self, ctx, event):
        if event.get("type") != "input":
            return
        token = event.get("token")
        if self.view == "menu":
            self._handle_menu(ctx, token)
        elif self.view == "vault":
            self._handle_vault(ctx, token)
        elif self.view == "create":
            self._handle_create(ctx, token)
        elif self.view == "delete":
            self._handle_delete(ctx, token)

    def _handle_menu(self, ctx, token):
        if token == "back":
            go_back(ctx, "launcher")
            return
        previous = self.menu_index
        self.menu_index = menu_move(token, self.menu_index, len(self.MENU_ITEMS))
        if previous != self.menu_index:
            self.mark_dirty()
            return
        if token in ("ok", "exe"):
            self.view = ("vault", "create", "delete")[self.menu_index]
            self.message = ""
            self.mark_dirty()

    def _handle_vault(self, ctx, token):
        if token == "back":
            self.view = "menu"
            self.mark_dirty()
            return
        if token == "nav_u":
            self.vault_scroll = clamp_scroll(self._vault_lines(ctx), self.vault_scroll - 1)
            self.mark_dirty()
            return
        if token == "nav_d":
            self.vault_scroll = clamp_scroll(self._vault_lines(ctx), self.vault_scroll + 1)
            self.mark_dirty()

    def _handle_create(self, ctx, token):
        keys = ("name", "variables", "expression")
        if token == "back":
            self.view = "menu"
            self.mark_dirty()
            return
        previous = self.create_selected
        self.create_selected = menu_move(token, self.create_selected, len(keys))
        if previous != self.create_selected:
            self.mark_dirty()
            return
        if token == "exe" or (token == "ok" and self.create_selected == len(keys) - 1):
            self._save(ctx)
            return
        if token == "ok":
            self.create_selected = min(len(keys) - 1, self.create_selected + 1)
            self.mark_dirty()
            return
        key = keys[self.create_selected]
        updated = apply_text_edit(self.form[key], token)
        if updated != self.form[key]:
            self.form[key] = updated
            self.mark_dirty()

    def _handle_delete(self, ctx, token):
        items = self._functions(ctx)
        if token == "back":
            self.view = "menu"
            self.mark_dirty()
            return
        if not items:
            return
        previous = self.delete_index
        self.delete_index = menu_move(token, self.delete_index, len(items))
        if previous != self.delete_index:
            self.mark_dirty()
            return
        if token in ("ok", "exe"):
            ctx.storage.delete_function(items[self.delete_index].get("name"))
            self.delete_index = 0
            self.message = "Function deleted."
            self.mark_dirty()

    def _vault_lines(self, ctx):
        lines = []
        for item in self._functions(ctx):
            variables = ",".join(item.get("variables", []))
            lines.append("%s(%s)" % (item.get("name", "?"), variables))
            lines.append("= %s" % item.get("expression", ""))
            lines.append("")
        if not lines:
            return ["No saved functions."]
        while lines and not lines[-1]:
            lines.pop()
        return lines

    def render(self, ctx):
        if self.view == "menu":
            return MenuScreen(self.manifest.title, self.MENU_ITEMS, selected=self.menu_index, footer=ctx.input.mode_label())
        if self.view == "vault":
            return TextScreen(self.manifest.title, self._vault_lines(ctx), footer="back=menu", scroll=self.vault_scroll)
        if self.view == "create":
            return FormScreen(
                self.manifest.title,
                fields_from_pairs(
                    [
                        ("name", "Name", self.form["name"]),
                        ("variables", "Vars", self.form["variables"]),
                        ("expression", "Expr", self.form["expression"]),
                    ]
                ),
                selected=self.create_selected,
                footer=ctx.input.mode_label(),
                message=self.message or "vars: x,y or blank",
            )
        items = [item.get("name", "?") for item in self._functions(ctx)] or ["No functions."]
        return MenuScreen(self.manifest.title, items, selected=min(self.delete_index, len(items) - 1), footer="OK deletes")


def create_app(manifest):
    return FunctionLockerApp(manifest)
