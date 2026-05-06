import asyncio
import os
import re


def _normalize_text(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[_-]+", " ", text)
    text = re.sub(r"[^a-z0-9\s']", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _extract_objects(context: dict):
    objects = []
    for entry in context.get("objects", []):
        name = _normalize_text(str(entry.get("name", "")))
        object_id = entry.get("id")
        if not name or not object_id:
            continue
        aliases = {name}
        for alias in entry.get("aliases", []):
            alias = _normalize_text(str(alias))
            if alias:
                aliases.add(alias)
        objects.append(
            {
                "id": str(object_id),
                "name": name,
                "aliases": sorted(aliases),
            }
        )
    return objects


def _extract_exits(context: dict):
    room = context.get("room", {})
    exits = []
    for exit_name in room.get("exits", []):
        exit_name = _normalize_text(str(exit_name))
        if exit_name:
            exits.append(exit_name)
    return sorted(set(exits))


def _find_object(normalized: str, objects):
    for obj in objects:
        for alias in obj["aliases"]:
            if alias and alias in normalized:
                return obj
    return None


async def _mock_interpret_command(input_text: str, context: dict) -> dict:
    await asyncio.sleep(0)

    normalized = _normalize_text(input_text)
    objects = _extract_objects(context)
    exits = _extract_exits(context)

    obj = _find_object(normalized, objects)

    if obj and any(phrase in normalized for phrase in ("pick up", "pick", "grab", "take")):
        return {
            "status": "done",
            "action": "take",
            "command": f"take {obj['name']}",
            "args": [obj["name"]],
            "target_id": obj["id"],
            "confidence": 84,
            "reason": "mock semantic provider mapped pickup phrasing to take",
            "provider": "mock",
        }

    if obj and any(phrase in normalized for phrase in ("look at", "inspect", "examine")):
        return {
            "status": "done",
            "action": "look",
            "command": f"look {obj['name']}",
            "args": [obj["name"]],
            "target_id": obj["id"],
            "confidence": 81,
            "reason": "mock semantic provider mapped inspection phrasing to look",
            "provider": "mock",
        }

    if obj and any(phrase in normalized for phrase in ("talk to", "ask", "speak to")):
        return {
            "status": "done",
            "action": "talk",
            "command": f"talk {obj['name']}",
            "args": [obj["name"]],
            "target_id": obj["id"],
            "confidence": 79,
            "reason": "mock semantic provider mapped speech phrasing to talk",
            "provider": "mock",
        }

    for exit_name in exits:
        if normalized == exit_name or normalized.endswith(f" {exit_name}"):
            return {
                "status": "done",
                "action": "go",
                "command": f"go {exit_name}",
                "args": [exit_name],
                "target_id": f"exit:{exit_name}",
                "confidence": 77,
                "reason": "mock semantic provider mapped movement phrasing to go",
                "provider": "mock",
            }

    return {
        "status": "done",
        "action": 0,
        "command": 0,
        "args": [],
        "target_id": 0,
        "confidence": 0,
        "reason": "mock semantic provider could not infer an action",
        "provider": "mock",
    }


async def interpret_command(input_text: str, context: dict) -> dict:
    provider = os.environ.get("SBLIB_AI_PROVIDER", "mock")
    if provider == "mock":
        return await _mock_interpret_command(input_text, context)
    if provider == "openai":
        raise RuntimeError(
            "OpenAI provider is not implemented yet; set SBLIB_AI_PROVIDER=mock "
            "for plumbing tests."
        )
    raise RuntimeError(f"Unsupported AI provider '{provider}'")
