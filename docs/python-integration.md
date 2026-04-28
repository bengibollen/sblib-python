# Python integration

This document summarizes how Python integrates with **LDMud**: how startup works, what the built-in `ldmud` module exposes, how Python efuns and types are registered, and which Python protocols LDMud understands.

## Overview

LDMud can execute Python code during driver startup. That startup code can import the built-in `ldmud` module and use it to:

- register new efuns
- register new LPC-visible types
- register hooks and sockets
- inspect driver objects, functions, variables, and closures

Python efuns behave much like native efuns from LPC's point of view. They can also shadow existing efuns, so registration timing matters.

## Startup model

The driver can start Python in two forms:

1. **A single script file**
2. **A package with a `__main__` module**

The startup code runs before the master object is loaded. If a package is used, the package itself is added to `sys.path`, so sibling modules can be imported normally.

Typical startup responsibilities are:

- importing integration modules
- registering efuns and types
- registering hooks
- loading configuration needed before LPC code starts depending on the registered features

## The `ldmud` module

The built-in `ldmud` module is only available inside the LDMud process. Its most important registration functions are:

| Function | Purpose |
| --- | --- |
| `register_efun(name, function)` | Register a Python function as an LPC efun |
| `unregister_efun(name)` | Remove a previously registered Python efun |
| `register_type(name, class)` | Register a Python class as an LPC-visible type |
| `unregister_type(name)` | Remove a previously registered Python type |
| `register_struct(name, base, fields)` | Define a global struct |
| `unregister_struct(name)` | Remove a previously registered struct |
| `register_hook(hook, function)` | Subscribe a Python callback to a driver hook |
| `unregister_hook(hook, function)` | Remove a hook callback |
| `register_socket(fd, function[, eventmask])` | Watch a file descriptor for poll/select events |
| `unregister_socket(fd)` | Stop watching a file descriptor |
| `get_master()` | Return the current master object, or `None` |
| `get_simul_efun()` | Return the current simul-efun object, or `None` |

### Registration constraints

- Registering or unregistering efuns and types is not allowed while an LPC object is being compiled.
- Removing an efun or type only affects newly compiled code.
- Previously compiled LPC code may continue calling old definitions or may raise runtime errors, depending on what changed.

## Defining Python efuns

A Python efun is just a Python callable registered with `ldmud.register_efun()`.

```python
import ldmud

def hello_world(name: str) -> int:
    print("Hello, world, %s!\n" % (name,))
    return 1

ldmud.register_efun("hello", hello_world)
```

### Type annotations matter

For registered efuns, Python annotations are not just documentation:

- argument annotations are used for type checking
- return annotations are used for type checking
- checks happen at both compile time and runtime
- LPC union types are expressed as Python tuples of types

Examples:

- `str` maps to LPC `string`
- `int` maps to LPC `int`
- `(str, int)` means a union of `string|int`
- `None` corresponds to LPC `void` in type definitions

### Name resolution and shadowing

Python efuns participate in function lookup similarly to simul-efuns. Without the `efun::` prefix, the lookup order is:

1. lfuns
2. simul-efuns
3. python efuns
4. real efuns

Because of that:

- a Python efun can shadow a real efun
- code compiled before registration may still call the old target
- code compiled after registration uses the Python efun
- unregistering an efun can leave previously compiled code with runtime errors

If an efun should affect normal LPC code reliably, register it during Python startup rather than later.

## Built-in Python-facing LDMud types

The `ldmud` module exposes Python classes for core LPC values. Common ones include:

| Python class | LPC concept |
| --- | --- |
| `Object` | regular LPC object |
| `LWObject` | lightweight object |
| `Array` | LPC array |
| `Mapping` | LPC mapping |
| `Struct` | LPC struct |
| `Closure` and subclasses | LPC closures |

### Value mapping

Basic LPC values map to Python values like this:

| LPC | Python |
| --- | --- |
| `int` | `int` / `bool` |
| `float` | `float` |
| `string` | `str` |
| `bytes` | `bytes` |

Type definitions map similarly, with two important additions:

| LPC type definition | Python |
| --- | --- |
| `void` | `None` |
| union | tuple of Python types |

### Typed container forms

Several exposed types can be subscripted to create more specific type objects:

- `Object["/path"]`
- `LWObject["/path"]`
- `Array[ElementType]`
- `Struct[program, name]`

These are useful for type checks and annotations in registered efuns or Python-backed LPC types.

## Registering Python-backed LPC types

`register_type(name, class)` makes a Python class visible to LPC as a named type. That type name becomes reserved during LPC compilation and can be used in normal LPC type declarations.

Registering a type does **not** automatically provide a constructor in LPC. If LPC code should be able to create instances, you normally also register one or more efuns that return the type.

## Python type protocol recognized by LDMud

Python objects are opaque in LPC by default, but they become much more useful when they implement special methods that LDMud understands.

### Operator hooks

LDMud can map LPC operations onto Python special methods, including:

- arithmetic: `__add__`, `__sub__`, `__mul__`, `__truediv__`, `__mod__`
- bitwise and shift operations
- comparisons
- in-place forms such as `__iadd__`
- reverse forms such as `__radd__`

Those methods can also carry annotations for compile-time type checking.

### Efun extension hooks

If the first argument to an efun is a Python object, LDMud may dispatch to a method named like:

```python
__efun_<name>__
```

For example, a Python type can implement:

```python
def __efun_call_other__(self, fun: str, *args):
    ...
```

This lets Python-backed types participate in existing efun-style operations.

### Persistence and conversion hooks

LDMud also understands these support methods:

| Method | Used for |
| --- | --- |
| `__repr__` | `sprintf()` string representation |
| `__copy__` | `copy()` / `deep_copy()` behavior |
| `__save__` | `save_value()` / `save_object()` |
| `__restore__` | `restore_value()` / `restore_object()` |
| `__convert__` | `to_type()` conversions |

Notes:

- `__restore__` should be a static method
- `__save__` should return an LPC-compatible value
- `__convert__` receives the target type and conversion options

## Hooks

`register_hook()` lets Python subscribe to driver events. Common hooks include:

- `ON_HEARTBEAT`
- `ON_OBJECT_CREATED`
- `ON_OBJECT_DESTRUCTED`
- `ON_CHILD_PROCESS_TERMINATED`
- signal hooks such as `ON_SIGINT`, `ON_SIGTERM`, `ON_SIGHUP`, `ON_SIGUSR1`, `ON_SIGUSR2`
- `BEFORE_INSTRUCTION`

Hook callbacks receive arguments based on the hook. For example:

- object lifecycle hooks receive the relevant object
- `BEFORE_INSTRUCTION` receives the current object and an instruction descriptor

## Sockets

`register_socket(fd, function[, eventmask])` integrates file descriptors into the driver's event loop. The `fd` can be:

- an integer file descriptor, or
- an object with a `fileno()` method

The callback receives the event mask. The mask can be built from values such as:

- `select.POLLIN`
- `select.POLLOUT`
- `select.POLLPRI`

## Object and closure introspection

LDMud's Python API exposes rich metadata for objects and closures. Depending on the object type, you can inspect:

- object name and program name
- visible functions
- variables
- function arguments and return types
- variable values and types
- closure bindings and ownership

This makes Python useful not just for adding efuns, but also for runtime inspection, debugging, and tooling.

## Practical guidelines

1. Register efuns and types as early as possible in startup.
2. Use annotations deliberately; they affect LPC type checking.
3. Treat efun names as part of the LPC API surface, because they participate in normal LPC name resolution.
4. When defining custom types, implement only the special methods you actually want LPC to support.
5. Be careful when unregistering or replacing efuns after LPC code has already been compiled.

## Minimal startup example

```python
import ldmud

def hello(name: str) -> int:
    print(f"Hello, {name}")
    return 1

def on_created(ob):
    print("created:", ob.name)

ldmud.register_efun("hello", hello)
ldmud.register_hook(ldmud.ON_OBJECT_CREATED, on_created)
```

## Summary

LDMud's Python integration is more than an embedded scripting hook. It provides:

- startup-time extension loading
- efun and type registration
- typed interop between LPC and Python
- Python-backed LPC types with operator and persistence hooks
- runtime inspection, hooks, and event integration

Used carefully, it allows Python code to behave like a first-class extension layer for the driver.
