from sblib import runtime


def startup() -> None:
    """Register the Python modules that belong to this mudlib."""

    try:
        import ldmud_asyncio  # type: ignore # noqa: F401
        print("Enabled Python asyncio integration")
    except ModuleNotFoundError:
        print("Warning: ldmud_asyncio not installed; async AI efuns will fail.")

    runtime.register_core_efuns()
    runtime.register_modules()
