import html as _html
import re
import uuid
from collections.abc import AsyncGenerator

import markdown as _md
from litestar import get
from litestar.exceptions import HTTPException
from litestar.response import ServerSentEvent
from litestar.types import SSEData

from guess_explainr.ai import stream_analysis


def _render(text: str) -> str:
    # The Markdown library requires a blank line before a list when it follows
    # a paragraph; LLMs often omit that blank line, so we insert it.
    text = re.sub(r"(?m)(?<=[^\n])\n([ \t]*[*\-+] )", r"\n\n\1", text)
    return _md.markdown(text, extensions=["extra"])


@get("/chat")
async def chat(message: str, context: str = "") -> ServerSentEvent:
    if not message:
        raise HTTPException(status_code=400, detail="message is required")

    async def _stream() -> AsyncGenerator[SSEData, None]:
        mock = (
            f"This is a mock response to: **{message}**. "
            "Real answers will come from the configured LLM. "
            "The context was: " + (context or "(none)") + "."
        )
        rendered = _render(mock)
        yield {"data": rendered, "event": "done"}

    return ServerSentEvent(_stream())


@get("/new-chat-id")
async def new_chat_id() -> dict:
    return {"id": str(uuid.uuid4())}


@get("/analysis-stream")
async def analysis_stream(countries: str, questions: str = "") -> ServerSentEvent:
    country_ids = [c.strip() for c in countries.split(",") if c.strip()]
    if not country_ids:
        raise HTTPException(status_code=400, detail="countries is required")

    async def _stream() -> AsyncGenerator[SSEData, None]:
        try:
            rendered = ""
            async for partial_text in stream_analysis(country_ids, questions, only_delta=False):
                rendered = _render(partial_text)
                yield {"data": rendered, "event": "msg"}
            yield {"data": rendered, "event": "done"}
        except Exception as e:
            error_html = f'<p class="text-error">{_html.escape(str(e))}</p>'
            yield {"data": error_html, "event": "done"}

    return ServerSentEvent(_stream())
