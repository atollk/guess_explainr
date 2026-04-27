from pathlib import Path

from litestar import Router, get

from guess_explainr.routes.panorama import panorama_image
from guess_explainr.routes.plonkit import plonkit_status
from guess_explainr.routes.step1 import get_config, get_models, save_config
from guess_explainr.routes.step2 import process_url
from guess_explainr.routes.step3 import compare
from guess_explainr.routes.step4 import analysis_stream, chat, new_chat_id

_SPA_INDEX = Path(__file__).parent.parent / "static" / "app" / "index.html"


@get("/", media_type="text/html")
async def index() -> bytes:
    return _SPA_INDEX.read_bytes()


api_router = Router(
    path="/api",
    route_handlers=[
        get_models,
        get_config,
        save_config,
        process_url,
        panorama_image,
        plonkit_status,
        compare,
        analysis_stream,
        chat,
        new_chat_id,
    ],
)

router = Router(path="/", route_handlers=[index])
