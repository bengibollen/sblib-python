# Async AI flow

This mudlib now separates AI command handling into two layers:

1. `ai_interpret_command()` for fast deterministic parsing
2. `ai_submit_intent()` / `ai_query_result()` for asynchronous semantic interpretation

The async layer is designed for **nonblocking** I/O and assumes the LDMud Python runtime has `ldmud_asyncio` installed and imported during startup.

## Startup dependency

`sblib.startup` tries to import:

```python
import ldmud_asyncio
```

If that import fails, the mudlib still starts, but async AI requests will return error results because there is no active asyncio integration.

Install it in the Python environment used by the mudlib:

```bash
pip install --user ldmud-asyncio
```

## Why HTTP first

The current design chooses **direct async HTTP-style integration** as the initial transport choice, not IPC.

Reasons:

- fewer moving parts
- simpler deployment in a private mudlib
- easy to replace later with IPC behind the same provider interface

If a future provider library is blocking or heavy, the mudlib API can stay the same while `sblib.ai.providers` is swapped to a local worker process.

## Modules

The async subsystem lives under `sblib.ai`:

- `sblib.ai.store` - in-memory request/result store
- `sblib.ai.service` - asyncio task lifecycle
- `sblib.ai.providers` - provider abstraction

`python_reload()` reloads these support modules before re-registering efuns.

## Efun API

### Submit

```lpc
string ai_submit_intent(string input, mapping context)
```

Queues an asynchronous semantic interpretation request and returns a request id immediately.

### Query

```lpc
mapping ai_query_result(string request_id)
```

Returns `0` while the request is pending. Once finished, returns a mapping with:

```lpc
([
  "request_id": <string>,
  "status": "done" | "error",
  "player_id": <string|0>,
  "action": <string|0>,
  "command": <string|0>,
  "args": <string*>,
  "target_id": <string|0>,
  "confidence": <int>,
  "reason": <string|0>,
  "provider": <string|0>,
])
```

For errors, the result contains:

```lpc
([
  "request_id": <string>,
  "status": "error",
  "player_id": <string|0>,
  "message": <string>,
])
```

### Discard

```lpc
int ai_discard_result(string request_id)
```

Removes a completed request result. If the request is still pending, it is cancelled first.

## Current provider behavior

The provider layer currently defaults to:

```text
SBLIB_AI_PROVIDER=mock
```

The mock provider is there to validate the async plumbing before real model calls are wired in. It can recognize some natural-language-like phrases such as:

- pick up / grab -> `take`
- inspect / look at -> `look`
- talk to / ask -> `talk`
- exit-like movement phrasing -> `go`

If you set:

```text
SBLIB_AI_PROVIDER=openai
```

the service currently returns an error because the real OpenAI HTTP provider has not been implemented yet.

## Suggested LPC flow

1. parser fails to resolve a command
2. call `ai_interpret_command(input, context)`
3. if result is a strong deterministic match, handle it immediately
4. if result is `"status": "none"` and `"classification": "natural_language"`, call `ai_submit_intent(input, context)`
5. store the returned request id on the player/session
6. poll with `ai_query_result(request_id)` until it resolves
7. consume the result and then call `ai_discard_result(request_id)`

## Notes

- Requests expire automatically after a short TTL.
- Pending async requests are cancelled during `python_reload()`.
- The current store is in-process memory only; a full driver restart clears it.
