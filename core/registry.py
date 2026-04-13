import json
import os

from .contracts import AppManifest


def _import_module(module_name):
    module = __import__(module_name, None, None, ["*"])
    return module


class AppRegistry:
    def __init__(self):
        self._manifests = {}

    def load_manifest_dir(self, manifest_dir):
        names = sorted(os.listdir(manifest_dir))
        for name in names:
            if not name.endswith(".json"):
                continue
            path = manifest_dir + "/" + name
            with open(path, "r") as handle:
                payload = json.load(handle)
            for item in payload:
                manifest = AppManifest.from_dict(item)
                self.register_manifest(manifest)

    def register_manifest(self, manifest):
        self._manifests[manifest.app_id] = manifest

    def sync_installed(self, installed_app_ids):
        installed_app_ids = set(installed_app_ids or [])
        for manifest in self._manifests.values():
            if manifest.kind == "optional":
                manifest.installed = manifest.app_id in installed_app_ids

    def get(self, app_id):
        return self._manifests.get(app_id)

    def list_group(self, group, include_disabled=False):
        results = []
        for manifest in self._manifests.values():
            if manifest.group != group:
                continue
            if not include_disabled and not manifest.enabled:
                continue
            if not manifest.installed:
                continue
            results.append(manifest)
        results.sort(key=lambda item: (item.order, item.title.lower()))
        return results

    def create(self, app_id):
        manifest = self.get(app_id)
        if manifest is None or not manifest.enabled or not manifest.installed:
            raise KeyError("unknown app: %s" % app_id)
        module = _import_module(manifest.module)
        factory = getattr(module, manifest.factory)
        return factory(manifest)
