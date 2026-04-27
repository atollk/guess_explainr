import uuid
from collections.abc import AsyncGenerator

from litestar import get
from litestar.exceptions import HTTPException
from litestar.response import ServerSentEvent, ServerSentEventMessage
from litestar.types import SSEData
from pydantic import BaseModel

from guess_explainr.ai import stream_analysis


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
        yield {"data": mock, "event": "done"}

    return ServerSentEvent(_stream())


class _NewChatIdResponse(BaseModel):
    id: str


@get("/new-chat-id")
async def new_chat_id() -> _NewChatIdResponse:
    return _NewChatIdResponse(id=str(uuid.uuid4()))


@get("/analysis-stream")
async def analysis_stream(countries: str, questions: str = "") -> ServerSentEvent:
    country_ids = [c.strip() for c in countries.split(",") if c.strip()]
    if not country_ids:
        raise HTTPException(status_code=400, detail="countries is required")

    async def _stream() -> AsyncGenerator[ServerSentEventMessage, None]:
        try:
            partial_text = ""
            async for partial_text in stream_analysis(country_ids, questions, only_delta=False):
                yield ServerSentEventMessage(data=partial_text, event="msg")
            yield ServerSentEventMessage(data=partial_text, event="done")
        except Exception as e:
            yield ServerSentEventMessage(data=str(e), event="error")

    return ServerSentEvent(_stream())
