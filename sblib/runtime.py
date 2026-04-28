import importlib
import sys
import traceback

import ldmud

MODULES = (
    "sblib.efuns.help",
    "sblib.efuns.reload",
    "sblib.efuns.json",
)

RELOADABLE_MODULES = tuple(
    module_name for module_name in MODULES if module_name != "sblib.efuns.reload"
)

_registered_efuns = {}
_registered_types = {}


def register_efun(name: str, function) -> None:
    _registered_efuns[name] = function
    ldmud.register_efun(name, function)


def register_type(name: str, cls) -> None:
    _registered_types[name] = cls
    ldmud.register_type(name, cls)


def get_registered_efun(name: str):
    return _registered_efuns.get(name)


def get_registered_type(name: str):
    return _registered_types.get(name)


def register_modules(module_names=MODULES) -> None:
    for module_name in module_names:
        try:
            print("Registering Python module", module_name)
            importlib.import_module(module_name).register()
        except Exception:
            traceback.print_exc()


def reload_modules(module_names=RELOADABLE_MODULES) -> None:
    for module_name in module_names:
        module = sys.modules.get(module_name)
        if module is None:
            continue

        try:
            on_reload = getattr(module, "on_reload", None)
            if on_reload is not None:
                on_reload()
        except Exception:
            traceback.print_exc()

        importlib.reload(module)
        print("Reload module", module_name)

    register_modules()
