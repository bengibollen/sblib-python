import difflib
import re

import ldmud

from sblib.ai import service
from sblib import runtime


MAX_INPUT_LENGTH = 120
DIRECT_MATCH_THRESHOLD = 92
SUGGESTION_THRESHOLD = 78
LLM_READY_THRESHOLD = 55


def to_python(value):
    if isinstance(value, ldmud.Array):
        return [to_python(item) for item in value]
    if isinstance(value, ldmud.Mapping):
        return {to_python(key): to_python(item) for key, item in dict(value).items()}
    return value


def to_lpc(value):
    if isinstance(value, dict):
        return ldmud.Mapping({key: to_lpc(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return ldmud.Array([to_lpc(item) for item in value])
    if value is None:
        return 0
    return value


def normalize_text(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[_-]+", " ", text)
    text = re.sub(r"[^a-z0-9\s']", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def split_tokens(text: str):
    if not text:
        return []
    return text.split(" ")


def has_gibberish_shape(normalized: str) -> bool:
    if not normalized:
        return True

    letters = [char for char in normalized if char.isalpha()]
    if not letters:
        return True

    if len(normalized) > MAX_INPUT_LENGTH:
        return True

    alnum_count = sum(char.isalnum() for char in normalized)
    if alnum_count / len(normalized) < 0.55:
        return True

    if " " not in normalized and len(normalized) >= 7:
        vowel_count = sum(char in "aeiouy" for char in letters)
        if vowel_count / len(letters) < 0.2:
            return True

        consonant_streak = 0
        longest_consonant_streak = 0
        for char in letters:
            if char in "aeiouy":
                consonant_streak = 0
            else:
                consonant_streak += 1
                longest_consonant_streak = max(
                    longest_consonant_streak, consonant_streak
                )
        if longest_consonant_streak >= 6:
            return True

    return False


def classify_input(normalized: str) -> str:
    if has_gibberish_shape(normalized):
        return "reject"
    if len(split_tokens(normalized)) >= 3:
        return "natural_language"
    return "command_like"


def make_result(
    *,
    status: str,
    confidence: int = 0,
    action: str = None,
    command: str = None,
    args=None,
    target_id: str = None,
    message: str = None,
    reason: str = None,
    classification: str = None,
):
    return {
        "status": status,
        "confidence": confidence,
        "action": action or 0,
        "command": command or 0,
        "args": list(args or []),
        "target_id": target_id or 0,
        "message": message or 0,
        "reason": reason or 0,
        "classification": classification or 0,
    }


def extract_verbs(context):
    verbs = []
    for entry in context.get("verbs", []):
        entry = to_python(entry)
        canonical = normalize_text(str(entry.get("verb", "")))
        if not canonical:
            continue

        phrases = {canonical}
        for alias in entry.get("aliases", []):
            alias = normalize_text(str(alias))
            if alias:
                phrases.add(alias)

        verbs.append(
            {
                "verb": canonical,
                "phrases": sorted(phrases),
            }
        )
    return verbs


def extract_objects(context):
    objects = []
    for entry in context.get("objects", []):
        entry = to_python(entry)
        object_id = entry.get("id")
        name = normalize_text(str(entry.get("name", "")))
        if not object_id or not name:
            continue

        aliases = {name}
        for alias in entry.get("aliases", []):
            alias = normalize_text(str(alias))
            if alias:
                aliases.add(alias)

        objects.append(
            {
                "id": str(object_id),
                "name": name,
                "aliases": sorted(aliases),
                "kind": entry.get("kind", 0),
            }
        )
    return objects


def extract_exits(context):
    room = to_python(context.get("room", {}))
    exits = []
    for exit_name in room.get("exits", []):
        exit_name = normalize_text(str(exit_name))
        if exit_name:
            exits.append(exit_name)
    return sorted(set(exits))


def command_phrase_score(left: str, right: str) -> int:
    return round(difflib.SequenceMatcher(None, left, right).ratio() * 100)


def build_candidates(context):
    candidates = []
    verbs = extract_verbs(context)
    objects = extract_objects(context)
    exits = extract_exits(context)

    has_go_verb = any(entry["verb"] == "go" for entry in verbs)

    for verb_entry in verbs:
        for phrase in verb_entry["phrases"]:
            candidates.append(
                {
                    "phrase": phrase,
                    "action": verb_entry["verb"],
                    "args": [],
                    "target_id": 0,
                    "command": verb_entry["verb"],
                    "reason": f"matched verb '{verb_entry['verb']}'",
                }
            )
            for obj in objects:
                for alias in obj["aliases"]:
                    candidates.append(
                        {
                            "phrase": f"{phrase} {alias}",
                            "action": verb_entry["verb"],
                            "args": [obj["name"]],
                            "target_id": obj["id"],
                            "command": f"{verb_entry['verb']} {obj['name']}",
                            "reason": (
                                f"matched verb '{verb_entry['verb']}' and object "
                                f"'{obj['name']}'"
                            ),
                        }
                    )
            for exit_name in exits:
                candidates.append(
                    {
                        "phrase": f"{phrase} {exit_name}",
                        "action": verb_entry["verb"],
                        "args": [exit_name],
                        "target_id": f"exit:{exit_name}",
                        "command": f"{verb_entry['verb']} {exit_name}",
                        "reason": (
                            f"matched verb '{verb_entry['verb']}' and exit "
                            f"'{exit_name}'"
                        ),
                    }
                )

    for exit_name in exits:
        candidates.append(
                {
                    "phrase": exit_name,
                    "action": "go",
                    "args": [exit_name],
                    "target_id": f"exit:{exit_name}",
                    "command": f"go {exit_name}" if has_go_verb else exit_name,
                    "reason": f"matched exit '{exit_name}'",
                }
        )

    unique_candidates = {}
    for candidate in candidates:
        unique_candidates[candidate["phrase"]] = candidate

    return list(unique_candidates.values())


def fuzzy_recover(normalized: str, context):
    best_candidate = None
    for candidate in build_candidates(context):
        score = command_phrase_score(normalized, candidate["phrase"])
        if best_candidate is None or score > best_candidate["confidence"]:
            best_candidate = {
                "status": "fuzzy",
                "confidence": score,
                "action": candidate["action"],
                "command": candidate["command"],
                "args": candidate["args"],
                "target_id": candidate["target_id"],
                "message": f"Did you mean '{candidate['command']}'?",
                "reason": candidate["reason"],
            }

    return best_candidate


def ai_interpret_command(input_text: str, context: ldmud.Mapping) -> ldmud.Mapping:
    """
    SYNOPSIS

            mapping ai_interpret_command(string input, mapping context)

    DESCRIPTION
            Tries to interpret an unknown player command using deterministic
            heuristics. The returned mapping is intended for LPC-side unknown
            command handling.

            The current implementation has three stages:
            1. reject obvious gibberish or malformed input
            2. fuzzy-match against verbs, visible objects and exits
            3. signal whether the input looks meaningful enough for an eventual
               LLM fallback

            The expected context shape is a mapping that may contain:
            - "verbs": ({ ([ "verb": string, "aliases": string* ]) ... })
            - "objects": ({ ([ "id": string, "name": string, "aliases": string*,
                               "kind": string ]) ... })
            - "room": ([ "exits": string* ])

            The returned mapping contains at least:
            - "status": "reject", "fuzzy" or "none"
            - "confidence": int
            - "action": normalized verb or 0
            - "command": normalized suggestion or 0
            - "args": string*
            - "target_id": target identifier or 0
            - "message": suggestion text or 0
            - "reason": short explanation or 0
            - "classification": "reject", "command_like", "natural_language" or 0

    SEE ALSO
            python_reload(E)
    """

    python_context = to_python(context)
    normalized = normalize_text(input_text)
    classification = classify_input(normalized)

    if classification == "reject":
        return to_lpc(
            make_result(
                status="reject",
                confidence=0,
                reason="input does not look like a plausible command",
                classification=classification,
            )
        )

    fuzzy = fuzzy_recover(normalized, python_context)
    if fuzzy and fuzzy["confidence"] >= SUGGESTION_THRESHOLD:
        fuzzy["classification"] = classification
        if fuzzy["confidence"] >= DIRECT_MATCH_THRESHOLD:
            fuzzy["message"] = f"Interpret as '{fuzzy['command']}'."
        return to_lpc(fuzzy)

    reason = "no strong deterministic match"
    if classification == "natural_language" and fuzzy and fuzzy["confidence"] >= LLM_READY_THRESHOLD:
        reason = "input may need semantic interpretation"

    return to_lpc(
        make_result(
            status="none",
            confidence=fuzzy["confidence"] if fuzzy else 0,
            reason=reason,
            classification=classification,
        )
    )


def ai_submit_intent(input_text: str, context: ldmud.Mapping) -> str:
    """
    SYNOPSIS

            string ai_submit_intent(string input, mapping context)

    DESCRIPTION
            Queues asynchronous semantic command interpretation and returns a
            request id immediately.

            The actual work is performed by the async AI service layer. This
            efun should only be used after the cheap deterministic helper
            ai_interpret_command(E) has failed to find a strong match.

            The request can be checked later with ai_query_result(E) and removed
            with ai_discard_result(E).

    SEE ALSO
            ai_interpret_command(E), ai_query_result(E), ai_discard_result(E)
    """

    return service.submit_intent(input_text, to_python(context))


def ai_query_result(request_id: str):
    """
    SYNOPSIS

            mapping ai_query_result(string request_id)

    DESCRIPTION
            Returns 0 while the asynchronous request is still pending.

            Once finished, returns a mapping containing at least the request id,
            completion status, and either a normalized command result or an error
            message.

    SEE ALSO
            ai_submit_intent(E), ai_discard_result(E)
    """

    result = service.query_result(request_id)
    if result is None:
        return 0
    return to_lpc(result)


def ai_discard_result(request_id: str) -> int:
    """
    SYNOPSIS

            int ai_discard_result(string request_id)

    DESCRIPTION
            Removes a completed asynchronous AI result. If the request is still
            pending, it is cancelled first.

            Returns 1 if a request existed and was removed, 0 otherwise.

    SEE ALSO
            ai_submit_intent(E), ai_query_result(E)
    """

    return 1 if service.discard_result(request_id) else 0


def register() -> None:
    runtime.register_efun("ai_interpret_command", ai_interpret_command)
    runtime.register_efun("ai_submit_intent", ai_submit_intent)
    runtime.register_efun("ai_query_result", ai_query_result)
    runtime.register_efun("ai_discard_result", ai_discard_result)
