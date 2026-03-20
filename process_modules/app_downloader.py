import st7565 as display

# try:
#     import tools
#     if hasattr(display, "graphics") and not hasattr(display.graphics, "pixels_changed"):
#         display.graphics = tools.refresh(display.graphics, pixels_changed=200)
# except Exception:
#     pass

# Copyright (c) 2025 CalSci
# Licensed under the MIT License.

from tinydb import TinyDB, Query


class Apps():
    def __init__(self):
        self.db = TinyDB("db/installed_apps.json")
        self.app_query = Query()

    def insert(self, app_name, group_name="installed_apps"):
        self.db.insert({"app_name": app_name, "group_name": group_name})
        return True

    def search_app_name(self, app_name, group_name="installed_apps"):
        result = self.db.search(
            (self.app_query.app_name == app_name)
            & (self.app_query.group_name == group_name)
        )
        if len(result) == 0:
            return None
        return result

    def sea_by_g(self, group_name):
        return self.db.search(self.app_query.group_name == group_name)

    def get_group_apps(self, group_name="installed_apps"):
        res = self.sea_by_g(group_name)
        app_list = []
        for app in res:
            app_list.append(app["app_name"])
        return app_list
    
    def insert_new_app(self, app_name, group_name="installed_apps"): #insert new app
        app=self.search_app_name(app_name)
        if app == None:
            self.insert(app_name, group_name)
            return True
        return False

    def delete_app(self, app_name, group_name="installed_apps"):
        app = self.search_app_name(app_name)
        if app is None:
            return False
        self.db.remove(
            (self.app_query.app_name == app_name)
            & (self.app_query.group_name == group_name)
        )
        return True
