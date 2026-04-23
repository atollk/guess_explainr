from pathlib import Path

from litestar import Litestar
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.logging import LoggingConfig
from litestar.static_files import StaticFilesConfig
from litestar.template.config import TemplateConfig

from guess_explainr.routes.index import api_router, router

BASE_PATH = Path(__file__).parent

logging_config = LoggingConfig(
    root={"level": "INFO"},
    log_exceptions="always",
)

app = Litestar(
    route_handlers=[router, api_router],
    template_config=TemplateConfig(
        directory=BASE_PATH / "templates",
        engine=JinjaTemplateEngine,
    ),
    static_files_config=[
        StaticFilesConfig(
            directories=[BASE_PATH / "static"],
            path="/static",
        ),
    ],
    logging_config=logging_config,
)
