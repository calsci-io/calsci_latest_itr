# Copyright (c) 2025 CalSci
# Licensed under the MIT License.

import gc
import sys


GROUP_ALIASES = {
    None: "root",
    "": "root",
    "application_modules": "root",
    "matrix_operations": "scientific_calculator",
}


class AppLoadError(Exception):
    pass


class LoadedApp:
    def __init__(self, route, module_name, module, runtime_app):
        self.route = route
        self.module_name = module_name
        self.module = module
        self.runtime_app = runtime_app


class RuntimeApp:
    def on_init(self):
        return None

    def run(self):
        raise NotImplementedError

    def on_exit(self):
        return None


class ClassAppAdapter(RuntimeApp):
    def __init__(self, instance):
        self.instance = instance

    def on_init(self):
        handler = getattr(self.instance, "on_init", None)
        if handler is not None:
            return handler()
        return None

    def run(self):
        handler = getattr(self.instance, "run", None)
        if handler is None:
            raise AppLoadError("App class is missing run()")
        return handler()

    def on_exit(self):
        handler = getattr(self.instance, "on_exit", None)
        if handler is not None:
            return handler()
        return None


class FunctionAppAdapter(RuntimeApp):
    def __init__(self, handler, pass_ctx=False, ctx=None):
        self.handler = handler
        self.pass_ctx = pass_ctx
        self.ctx = ctx

    def run(self):
        if self.pass_ctx:
            return self.handler(self.ctx)
        return self.handler()


def normalize_route(app_name, group_name):
    if not app_name:
        app_name = "home"

    group_name = GROUP_ALIASES.get(group_name, group_name)
    if not group_name:
        group_name = "root"

    return app_name, group_name


def resolve_next_route(ctx):
    return normalize_route(*ctx.app.next_route())


def _walk_import(module_name):
    module = __import__(module_name)
    for part in module_name.split(".")[1:]:
        module = getattr(module, part)
    return module


def _module_name(route):
    return "apps.{0}.{1}".format(route[1], route[0])


def _class_accepts_ctx(app_class):
    init = getattr(app_class, "__init__", None)
    code = getattr(init, "__code__", None)
    argcount = getattr(code, "co_argcount", None)
    if argcount is None:
        return True
    return argcount > 1


def _function_accepts_ctx(handler):
    code = getattr(handler, "__code__", None)
    argcount = getattr(code, "co_argcount", None)
    if argcount is None:
        return True
    return argcount > 0


def _build_runtime_app(ctx, module, app_name):
    app_class = getattr(module, "App", None)
    if app_class is not None:
        instance = app_class(ctx) if _class_accepts_ctx(app_class) else app_class()
        return ClassAppAdapter(instance)

    run_handler = getattr(module, "run", None)
    if run_handler is not None:
        return FunctionAppAdapter(
            run_handler,
            pass_ctx=_function_accepts_ctx(run_handler),
            ctx=ctx,
        )

    legacy_handler = getattr(module, app_name, None)
    if legacy_handler is not None:
        return FunctionAppAdapter(legacy_handler)

    raise AppLoadError("No supported entry point found for {0}".format(app_name))


def load_app(ctx, route):
    route = normalize_route(route[0], route[1])
    module_name = _module_name(route)
    gc.collect()
    module = _walk_import(module_name)
    runtime_app = _build_runtime_app(ctx, module, route[0])
    return LoadedApp(route, module_name, module, runtime_app)


def _unload_module(module_name):
    to_remove = []
    prefix = module_name + "."

    for loaded_name in sys.modules:
        if loaded_name == module_name or loaded_name.startswith(prefix):
            to_remove.append(loaded_name)

    for loaded_name in to_remove:
        try:
            parent_name, child_name = loaded_name.rsplit(".", 1)
            parent_module = sys.modules.get(parent_name)
            if parent_module is not None and hasattr(parent_module, child_name):
                delattr(parent_module, child_name)
        except Exception:
            pass

        try:
            del sys.modules[loaded_name]
        except Exception:
            pass


def cleanup_loaded_app(ctx, loaded_app):
    loaded_app.runtime_app = None
    loaded_app.module = None
    ctx.app_state.clear()
    _unload_module(loaded_app.module_name)
    gc.collect()


def _print_exception(exc):
    printer = getattr(sys, "print_exception", None)
    if printer is not None:
        printer(exc)
    else:
        print(exc)


def run_loaded_app(ctx, loaded_app):
    run_error = None
    try:
        loaded_app.runtime_app.on_init()
        return loaded_app.runtime_app.run()
    except Exception as exc:
        run_error = exc
        raise
    finally:
        try:
            loaded_app.runtime_app.on_exit()
        except Exception as exit_exc:
            if run_error is None:
                run_error = exit_exc
                raise
            _print_exception(exit_exc)
        finally:
            cleanup_loaded_app(ctx, loaded_app)


def run_app_route(ctx, route):
    loaded_app = load_app(ctx, route)
    return run_loaded_app(ctx, loaded_app)
