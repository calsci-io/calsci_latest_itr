class AppContext:
    def __init__(self, router, state, bus, tasks, registry, services, config):
        self.router = router
        self.state = state
        self.bus = bus
        self.tasks = tasks
        self.registry = registry
        self.services = services
        self.config = config

    @property
    def input(self):
        return self.services["input"]

    @property
    def render(self):
        return self.services["render"]

    @property
    def storage(self):
        return self.services["storage"]

    @property
    def network(self):
        return self.services["network"]

    @property
    def power(self):
        return self.services["power"]

    @property
    def calc(self):
        return self.services.get("calc")

    @property
    def graph(self):
        return self.services.get("graph")

    @property
    def search(self):
        return self.services.get("search")

    @property
    def matrix(self):
        return self.services.get("matrix")

    @property
    def time(self):
        return self.services.get("time")

    @property
    def latex(self):
        return self.services.get("latex")

    @property
    def update(self):
        return self.services.get("update")

    def service(self, name):
        return self.services.get(name)

    def list_apps(self, group, include_disabled=False):
        return self.registry.list_group(group, include_disabled=include_disabled)
