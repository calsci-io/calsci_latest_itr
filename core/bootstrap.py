import json

from core.context import AppContext
from core.events import EventBus
from core.fscompat import root_dir_from_file
from core.legacy_import import ensure_manifest_layout
from core.registry import AppRegistry
from core.router import Router
from core.runtime import RuntimeKernel
from core.state_store import StateStore
from core.tasks import TaskManager

from adapters.device.display import DeviceDisplayAdapter
from adapters.device.input import DeviceInputAdapter
from adapters.device.network import DeviceNetworkAdapter
from adapters.device.power import DevicePowerAdapter
from adapters.device.storage import DeviceStorageAdapter

from services.calc_service import CalculatorService
from services.graph_service import GraphService
from services.input_service import InputService
from services.latex_service import LatexService
from services.matrix_service import MatrixService
from services.network_service import NetworkService
from services.power_service import PowerService
from services.render_service import RenderService
from services.search_service import SearchService
from services.storage_service import StorageService
from services.time_service import TimeService
from services.update_service import UpdateService


def _root_dir():
    return root_dir_from_file(__file__, levels=2)


def _load_json(path):
    with open(path, "r") as handle:
        return json.load(handle)


def build_container():
    root_dir = _root_dir()
    config = _load_json(root_dir + "/config/system.json")

    state = StateStore()
    bus = EventBus()
    tasks = TaskManager(bus, max_workers=config.get("task_workers", 2))

    storage_adapter = DeviceStorageAdapter(root_dir, config)
    storage_service = StorageService(storage_adapter, config)
    storage_service.ensure_runtime_ready()
    ensure_manifest_layout(root_dir, config.get("legacy_root"), storage_service)

    default_route = storage_service.get_setting("default_route", config.get("default_route", "launcher"))
    router = Router(initial_route=default_route)
    registry = AppRegistry()
    registry.load_manifest_dir(root_dir + "/config/apps")
    registry.sync_installed(storage_service.get_installed_apps())

    display_adapter = DeviceDisplayAdapter()
    display_adapter.init()
    input_adapter = DeviceInputAdapter()
    network_adapter = DeviceNetworkAdapter()
    power_adapter = DevicePowerAdapter()

    services = {
        "storage": storage_service,
        "render": RenderService(display_adapter, storage_service),
        "input": InputService(input_adapter, storage_service),
        "network": NetworkService(network_adapter, storage_service),
        "power": PowerService(power_adapter, storage_service),
        "calc": CalculatorService(storage_service),
        "graph": GraphService(),
        "matrix": MatrixService(),
    }
    services["search"] = SearchService(services["network"])
    services["time"] = TimeService(services["network"])
    services["latex"] = LatexService()
    services["update"] = UpdateService(services["network"], storage_service, config)

    ctx = AppContext(router, state, bus, tasks, registry, services, config)
    return {
        "ctx": ctx,
        "runtime": RuntimeKernel(ctx, initial_route=default_route),
        "config": config,
        "root_dir": root_dir,
    }


def boot():
    container = build_container()
    container["ctx"].storage.ensure_runtime_ready()
    return container


def main():
    container = build_container()
    container["runtime"].run()
