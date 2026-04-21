from pathlib import Path

from litestar import Litestar
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.static_files import StaticFilesConfig
from litestar.template.config import TemplateConfig

from geolearnr.routes.index import router

_BASE = Path(__file__).parent

app = Litestar(
    route_handlers=[router],
    template_config=TemplateConfig(
        directory=_BASE / "templates",
        engine=JinjaTemplateEngine,
    ),
    static_files_config=[
        StaticFilesConfig(
            directories=[_BASE / "static"],
            path="/static",
        ),
    ],
)
