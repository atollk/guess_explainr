from litestar import Router, get
from litestar.response import Template

from guess_explainr.routes.step1 import get_config, get_models, save_config
from guess_explainr.routes.step2 import process_url
from guess_explainr.routes.step3 import compare
from guess_explainr.routes.step4 import chat, new_chat_id


@get("/")
async def index() -> Template:
    return Template(template_name="wizard.html", context={"title": "Guess Explainr"})


api_router = Router(
    path="/api",
    route_handlers=[get_models, get_config, save_config, process_url, compare, chat, new_chat_id],
)

router = Router(path="/", route_handlers=[index])
