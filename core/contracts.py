class AppManifest:
    def __init__(
        self,
        app_id,
        title,
        module,
        group="home",
        order=100,
        enabled=True,
        kind="built_in",
        factory="create_app",
        installed=True,
        metadata=None,
    ):
        self.app_id = app_id
        self.title = title
        self.module = module
        self.group = group
        self.order = int(order)
        self.enabled = bool(enabled)
        self.kind = kind
        self.factory = factory
        self.installed = bool(installed)
        self.metadata = metadata or {}

    @classmethod
    def from_dict(cls, payload):
        return cls(
            app_id=payload["app_id"],
            title=payload.get("title", payload["app_id"]),
            module=payload["module"],
            group=payload.get("group", "home"),
            order=payload.get("order", 100),
            enabled=payload.get("enabled", True),
            kind=payload.get("kind", "built_in"),
            factory=payload.get("factory", "create_app"),
            installed=payload.get("installed", True),
            metadata=payload.get("metadata", {}),
        )

    def to_dict(self):
        return {
            "app_id": self.app_id,
            "title": self.title,
            "module": self.module,
            "group": self.group,
            "order": self.order,
            "enabled": self.enabled,
            "kind": self.kind,
            "factory": self.factory,
            "installed": self.installed,
            "metadata": self.metadata,
        }


class BaseApp:
    def __init__(self, manifest):
        self.manifest = manifest
        self._dirty = True

    def enter(self, ctx, params=None):
        self.mark_dirty()

    def handle_event(self, ctx, event):
        return None

    def render(self, ctx):
        raise NotImplementedError

    def exit(self, ctx):
        return None

    def mark_dirty(self):
        self._dirty = True

    def consume_dirty(self):
        dirty = self._dirty
        self._dirty = False
        return dirty

