import asyncio
from pathlib import Path

from litestar import Litestar
from litestar.logging import LoggingConfig
from litestar.static_files import create_static_files_router

from guess_explainr.plonkit_cache import sync_plonkit_files
from guess_explainr.routes.index import api_router, router

BASE_PATH = Path(__file__).parent

logging_config = LoggingConfig(
    root={"level": "INFO"},
    log_exceptions="always",
)

_plonkit_sync_task: asyncio.Task


async def _start_plonkit_sync(app: Litestar) -> None:
    global _plonkit_sync_task
    _plonkit_sync_task = asyncio.create_task(sync_plonkit_files())


app = Litestar(
    on_startup=[_start_plonkit_sync],
    route_handlers=[
        router,
        api_router,
        create_static_files_router(
            path="/static",
            directories=[BASE_PATH / "static"],
        ),
    ],
    logging_config=logging_config,
)
