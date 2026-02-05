# Copyright (c) 2025 CalSci
# Licensed under the MIT License.

import machine
import requests
from tinydb import Query, TinyDB


class Apps:
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
    
    def insert_new_app(self, app_name, group_name="installed_apps"):
        app = self.search_app_name(app_name)
        if app is None:
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

class App_downloader:
    def __init__(self):
        self.apps = Apps()
        self.mac = "".join("{:02X}".format(b) for b in machine.unique_id())
        self.app_name = ""

    def check_status(self):
        check_status_url = (
            "https://czxnvqwbwszzfgecpkbi.supabase.co/functions/v1/"
            f"check-pending-apps?macAddress={self.mac}"
        )
        res = requests.get(check_status_url).json()
        print(res)
        return res["response"] == "true"

    def download_app(self):
        download_url = (
            "https://czxnvqwbwszzfgecpkbi.supabase.co/functions/v1/"
            f"get-pending-apps?macAddress={self.mac}"
        )
        res = requests.get(download_url).json()
        print(res)
        self.app_name = res["app_name"]
        with open(f"/apps/installed_apps/{self.app_name}.py", "w") as app_file:
            app_file.write(res["code"])
        return True
    
    def update_app_list(self):
        self.apps.insert_new_app(self.app_name)
        return True

    def send_confirmation(self):
        confirmation_url = (
            "https://czxnvqwbwszzfgecpkbi.supabase.co/functions/v1/"
            f"confirm-download?macAddress={self.mac}"
        )
        res = requests.get(confirmation_url).json()
        print(res)
        return True

    def reset(self):
        from machine import reset
        reset()
        return True
