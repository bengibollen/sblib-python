import asyncio
import traceback

from sblib.ai import providers, store

_pending_tasks = {}


def _event_loop():
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.get_event_loop()


async def _run_interpret_command(request_id: str, input_text: str, context: dict) -> None:
    try:
        result = await providers.interpret_command(input_text, context)
        store.mark_done(request_id, result)
    except Exception as exc:
        traceback.print_exc()
        store.mark_error(request_id, str(exc))
    finally:
        _pending_tasks.pop(request_id, None)


def submit_intent(input_text: str, context: dict) -> str:
    request_id = store.create_request("interpret_command", input_text, context)
    try:
        task = _event_loop().create_task(
            _run_interpret_command(request_id, input_text, context)
        )
    except RuntimeError as exc:
        store.mark_error(
            request_id,
            (
                "No active asyncio loop. Make sure ldmud_asyncio is installed and "
                f"imported during startup ({exc})."
            ),
        )
        return request_id

    _pending_tasks[request_id] = task
    return request_id


def query_result(request_id: str):
    return store.read_result(request_id)


def discard_result(request_id: str) -> bool:
    task = _pending_tasks.pop(request_id, None)
    if task is not None:
        task.cancel()
    return store.discard_request(request_id)


def on_reload() -> None:
    for request_id, task in list(_pending_tasks.items()):
        task.cancel()
        store.mark_error(request_id, "cancelled during python_reload")
    _pending_tasks.clear()
