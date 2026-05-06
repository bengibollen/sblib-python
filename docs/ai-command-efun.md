# AI command efun

`ai_interpret_command()` is a deterministic first-pass helper for unknown command handling. It does **not** call an LLM yet. Its job is to reject obvious garbage input and recover likely commands from the local room/player context.

For the asynchronous semantic stage, see `docs/ai-async.md`.

## Efun

```lpc
mapping ai_interpret_command(string input, mapping context)
```

## Current behavior

The Python implementation currently does three things:

1. normalizes the raw input
2. rejects inputs that look like gibberish
3. fuzzy-matches against known verbs, visible objects, and room exits

If no strong deterministic match is found, it returns `"status": "none"` with a classification that can later be used to decide whether an LLM fallback is worth trying.

## Expected context

The efun accepts a mapping with a small, structured context. The current implementation reads these keys:

```lpc
([
  "verbs": ({
    ([ "verb": "look", "aliases": ({ "l", "examine", "inspect" }) ]),
    ([ "verb": "take", "aliases": ({ "get", "pick up" }) ]),
    ([ "verb": "go",   "aliases": ({ "walk", "move" }) ]),
  }),

  "objects": ({
    ([ "id": "room:rusty_key",
       "name": "rusty key",
       "aliases": ({ "key", "rusty key" }),
       "kind": "item" ]),

    ([ "id": "room:guard",
       "name": "guard",
       "aliases": ({ "guard", "watchman" }),
       "kind": "living" ]),
  }),

  "room": ([
    "exits": ({ "north", "south", "east" }),
  ]),
])
```

Only `verbs`, `objects`, and `room["exits"]` are used right now. Extra keys are ignored.

## Return value

The efun always returns a mapping with these keys:

```lpc
([
  "status": "reject" | "fuzzy" | "none",
  "confidence": <int>,
  "action": <string|0>,
  "command": <string|0>,
  "args": <string*>,
  "target_id": <string|0>,
  "message": <string|0>,
  "reason": <string|0>,
  "classification": "reject" | "command_like" | "natural_language" | 0,
])
```

### Meaning of the fields

| Key | Meaning |
| --- | --- |
| `status` | Overall result: reject, fuzzy suggestion, or no deterministic match |
| `confidence` | Similarity score from 0-100 |
| `action` | Normalized verb such as `look`, `take`, or `go` |
| `command` | Normalized suggested command such as `take rusty key` |
| `args` | Suggested string arguments |
| `target_id` | Stable object/exit identifier if a target was matched |
| `message` | Human-friendly suggestion text |
| `reason` | Short explanation for logging or debugging |
| `classification` | Rough input type after normalization |

## Example results

### Gibberish

```lpc
([
  "status": "reject",
  "confidence": 0,
  "action": 0,
  "command": 0,
  "args": ({ }),
  "target_id": 0,
  "message": 0,
  "reason": "input does not look like a plausible command",
  "classification": "reject",
])
```

### Strong fuzzy recovery

Input:

```text
taek key
```

Possible result:

```lpc
([
  "status": "fuzzy",
  "confidence": 90,
  "action": "take",
  "command": "take rusty key",
  "args": ({ "rusty key" }),
  "target_id": "room:rusty_key",
  "message": "Did you mean 'take rusty key'?",
  "reason": "matched verb 'take' and object 'rusty key'",
  "classification": "command_like",
])
```

### Meaningful but unresolved input

```lpc
([
  "status": "none",
  "confidence": 62,
  "action": 0,
  "command": 0,
  "args": ({ }),
  "target_id": 0,
  "message": 0,
  "reason": "input may need semantic interpretation",
  "classification": "natural_language",
])
```

## Suggested LPC-side usage

Use this efun as an unknown-command helper, not as an executor. A typical flow is:

1. parser fails to resolve the command
2. LPC builds the context mapping
3. LPC calls `ai_interpret_command(input, context)`
4. LPC decides what to do with the result

Recommended policy:

- `status == "reject"`: show ordinary unknown-command feedback
- `status == "fuzzy"` with high confidence: suggest or auto-rewrite, depending on your tolerance
- `status == "none"` and `classification == "natural_language"`: good candidate for future LLM fallback

## Notes

- The current scorer uses Python's standard library and is intentionally dependency-free.
- The efun is designed so a later LLM phase can reuse the same context and return format.
- `target_id` should be treated as advisory until LPC resolves it again in the current game state.
