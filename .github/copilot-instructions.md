# Copilot instructions

## Build, test, and lint

- This checkout does **not** include a checked-in test suite, lint config, or packaging files such as `setup.py`, `setup.cfg`, or `pyproject.toml`.
- The `*.egg-info/PKG-INFO` files preserve upstream install documentation, but those commands target source trees that are **not** present in this repository snapshot. Do not assume `python3 setup.py install --user` is runnable here.
- When validating changes, prefer small import/smoke checks around the modules you touched instead of inventing a new test harness.

## High-level architecture

- `__main__.py` is the bootstrap entry used to load Python efuns from this checkout. It appends the repository directory to `sys.path`, imports `ldmudefuns.startup.startup`, and runs it.
- That bootstrap shape matches LDMud's Python startup model: the driver can execute either a standalone script or a package with `__main__`, so repository-level startup behavior is intentionally concentrated in `__main__.py`.
- `ldmudefuns/startup.py` is the main registry loader. It reads `~/.ldmud-efuns`, discovers installed setuptools entry points with `importlib.metadata.entry_points()`, and registers enabled `ldmud_efun` and `ldmud_type` entries into the live `ldmud` runtime.
- `ldmudefuns/reload.py` mirrors the same discovery process for hot reloads. Before re-registering, it removes the affected module chain from `sys.modules` and calls an optional `on_reload()` hook if a module provides one.
- `ldmudefuns/help.py` is the introspection layer behind `python_efun_help`. It either reads live functions from `ldmud.registered_efuns` or loads the matching entry-point target directly, then returns a cleaned-up docstring.
- `ldmudefunalternatives/json.py` shows the pattern for an efun package that implements driver-like behavior in Python and registers exported efuns into LDMud.
- `disable/` contains extra efun/type packages and matching `egg-info` snapshots that are not part of the active startup path in this checkout. Treat them as disabled examples unless you are explicitly reviving one.

## Key conventions

- Runtime discovery is driven by setuptools entry-point groups named `ldmud_efun` and `ldmud_type`. The externally visible LPC name comes from the **entry-point name**, not from the Python symbol name.
- Loadable modules also tend to expose a zero-argument `register()` helper for manual startup scripts. If you add or rename an efun/type, keep the entry-point metadata and the manual `register()` path aligned.
- `~/.ldmud-efuns` is the per-user feature switchboard. Keys under `[efuns]` and `[types]` must match entry-point names exactly, so renaming an entry point is a behavioral change.
- Python type annotations are semantically important here, not just documentation: LDMud uses efun annotations for compile-time and runtime type checks, and this codebase also evaluates deferred annotations for custom registered types.
- Efun docstrings use LDMud-style sections such as `SYNOPSIS`, `DESCRIPTION`, and `SEE ALSO`. Preserve that format: `python_efun_help` returns those docstrings directly after PEP 257-style trimming.
- If you work on custom Python-backed LPC types, preserve LDMud protocol methods such as `__save__`/`__restore__` and any operator hooks already used by the type; those methods define how values round-trip through the driver.
- Keep the importlib compatibility shim intact unless the whole codebase is intentionally raised to newer Python-only support: modules first try `importlib.metadata` and fall back to `importlib_metadata`.
