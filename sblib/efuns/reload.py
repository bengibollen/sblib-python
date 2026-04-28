from sblib import runtime


def reload_modules():
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

    runtime.reload_modules()


def register() -> None:
    runtime.register_efun("python_reload", reload_modules)
