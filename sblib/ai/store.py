import time
import uuid


REQUEST_TTL_SECONDS = 300
_requests = {}


def _now() -> float:
    return time.time()


def purge_expired() -> None:
    now = _now()
    expired_ids = [
        request_id
        for request_id, entry in _requests.items()
        if entry["expires_at"] <= now
    ]
    for request_id in expired_ids:
        del _requests[request_id]


def create_request(kind: str, input_text: str, context: dict) -> str:
    purge_expired()
    request_id = str(uuid.uuid4())
    player = context.get("player", {}) if isinstance(context.get("player"), dict) else {}
    _requests[request_id] = {
        "id": request_id,
        "kind": kind,
        "status": "pending",
        "created_at": _now(),
        "expires_at": _now() + REQUEST_TTL_SECONDS,
        "input": input_text,
        "context": context,
        "player_id": player.get("id", 0),
        "result": None,
        "error": None,
    }
    return request_id


def get_request(request_id: str):
    purge_expired()
    return _requests.get(request_id)


def mark_done(request_id: str, result: dict) -> None:
    entry = get_request(request_id)
    if entry is None:
        return
    entry["status"] = "done"
    entry["result"] = result
    entry["error"] = None


def mark_error(request_id: str, message: str) -> None:
    entry = get_request(request_id)
    if entry is None:
        return
    entry["status"] = "error"
    entry["result"] = None
    entry["error"] = message


def read_result(request_id: str):
    entry = get_request(request_id)
    if entry is None:
        return None

    if entry["status"] == "pending":
        return None

    payload = {
        "request_id": request_id,
        "status": entry["status"],
        "player_id": entry["player_id"] or 0,
    }
    if entry["status"] == "done":
        payload.update(entry["result"])
    else:
        payload["message"] = entry["error"] or "unknown error"
    return payload


def discard_request(request_id: str) -> bool:
    purge_expired()
    return _requests.pop(request_id, None) is not None


def list_pending_ids():
    purge_expired()
    return [
        request_id
        for request_id, entry in _requests.items()
        if entry["status"] == "pending"
    ]
