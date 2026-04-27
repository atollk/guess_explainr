import asyncio
from pathlib import Path

from litestar import Litestar
from litestar.logging import LoggingConfig
from litestar.static_files import StaticFilesConfig

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
    route_handlers=[router, api_router],
    on_startup=[_start_plonkit_sync],
    static_files_config=[
        StaticFilesConfig(
            directories=[BASE_PATH / "static"],
            path="/static",
        ),
    ],
    logging_config=logging_config,
)
