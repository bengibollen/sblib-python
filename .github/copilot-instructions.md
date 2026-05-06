# Copilot instructions

## Build, test, and lint

- This checkout does **not** include a checked-in test suite, lint config, or packaging files such as `setup.py`, `setup.cfg`, or `pyproject.toml`.
- This repository is organized as private mudlib code, not a publishable Python package. Do not reintroduce setuptools entry-point discovery or `*.egg-info`-driven workflows unless explicitly asked.
- When validating changes, prefer small import/smoke checks around the modules you touched instead of inventing a new test harness.

## High-level architecture

- `__main__.py` is the bootstrap entry for LDMud. It appends the repository root to `sys.path`, imports `sblib.startup.startup`, and runs it.
- `sblib/startup.py` is the explicit startup path for this mudlib. It does not discover installed packages; it registers a fixed set of mudlib-owned Python modules.
- `sblib/runtime.py` is the central registry helper. It owns the list of active Python modules, registers core efuns such as `python_reload`, wraps `ldmud.register_efun()` / `register_type()`, keeps an in-process registry for help/introspection, and implements explicit module reloads.
- `sblib/startup.py` also tries to import `ldmud_asyncio`; async AI features rely on that package being installed in the mudlib runtime.
- `sblib/efuns/ai.py`, `sblib/efuns/help.py`, and `sblib/efuns/json.py` are the active efun modules loaded by startup.
- `sblib/ai/` contains the async AI subsystem: in-memory request store, async service layer, and provider adapters.
- `disable/` contains extra Python efun/type examples that are **not** part of the active startup path. Treat them as examples only unless you explicitly wire one into `sblib.runtime.MODULES`.

## Key conventions

- Active Python modules expose a zero-argument `register()` helper. To add a new efun module, add it to `sblib.runtime.MODULES` and implement `register()` there.
- The externally visible LPC name is the string passed to `runtime.register_efun()` / `runtime.register_type()`, so treat those names as API surface for the mudlib.
- Python type annotations are semantically important here, not just documentation: LDMud uses efun annotations for compile-time and runtime type checks, and this codebase also evaluates deferred annotations for custom registered types.
- Efun docstrings use LDMud-style sections such as `SYNOPSIS`, `DESCRIPTION`, and `SEE ALSO`. Preserve that format: `python_efun_help` returns those docstrings directly after PEP 257-style trimming.
- If you work on custom Python-backed LPC types, preserve LDMud protocol methods such as `__save__`/`__restore__` and any operator hooks already used by the type; those methods define how values round-trip through the driver.
- `python_reload` is core runtime functionality, not an efun module. It reloads the active efun modules from `sblib.runtime.MODULES` plus any support modules wired into `sblib.runtime`, then re-runs registration.
- Async AI requests are nonblocking by design: `ai_submit_intent()` should only queue work, while provider/network activity lives under `sblib.ai.service` and `sblib.ai.providers`.
