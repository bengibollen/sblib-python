import importlib
import sys
import traceback

import ldmud

MODULES = (
    "sblib.efuns.ai",
    "sblib.efuns.help",
    "sblib.efuns.json",
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


def python_reload():
    """
    SYNOPSIS
            void python_reload()

    DESCRIPTION
            Reloads the Python efun modules that are explicitly configured for
            this mudlib and registers them again.

            Before reloading, the function on_reload() is called in the module
            if it exists.

    SEE ALSO
            python_efun_help(E)
    """

    reload_modules()


def register_core_efuns() -> None:
    print("Registering core Python efuns")
    register_efun("python_reload", python_reload)


def register_modules(module_names=MODULES) -> None:
    for module_name in module_names:
        try:
            print("Registering Python module", module_name)
            importlib.import_module(module_name).register()
        except Exception:
            traceback.print_exc()


def reload_modules(module_names=MODULES) -> None:
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
