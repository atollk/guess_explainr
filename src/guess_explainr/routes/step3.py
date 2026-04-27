import urllib.parse

from litestar import post
from litestar.exceptions import HTTPException
from pydantic import BaseModel

from guess_explainr.models import CompareRequest


class _CompareResponse(BaseModel):
    stream_url: str
    context: str


@post("/compare")
async def compare(data: CompareRequest) -> _CompareResponse:
    if not data.compare_countries:
        raise HTTPException(status_code=400, detail="Select at least one country")
    countries_param = urllib.parse.quote(",".join(data.compare_countries))
    questions_param = urllib.parse.quote(data.questions or "")
    stream_url = f"/api/analysis-stream?countries={countries_param}&questions={questions_param}"
    return _CompareResponse(
        stream_url=stream_url,
        context=", ".join(data.compare_countries),
    )
