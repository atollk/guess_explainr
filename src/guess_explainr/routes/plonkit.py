from litestar import get

from guess_explainr import state


@get("/plonkit-status")
async def plonkit_status() -> dict:
    s = state.plonkit_sync_state
    return {
        "ready": s.ready,
        "done": s.done,
        "total": s.total,
        "error": s.error,
    }
