from sblib import runtime


def startup() -> None:
    """Register the Python modules that belong to this mudlib."""

    runtime.register_modules()
