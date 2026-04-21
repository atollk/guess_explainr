from litestar import Router, get
from litestar.response import Template


@get("/")
async def index() -> Template:
    return Template(template_name="index.html", context={"title": "GeoLearnr"})


router = Router(path="/", route_handlers=[index])
