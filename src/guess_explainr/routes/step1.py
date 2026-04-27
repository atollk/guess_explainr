from litestar import get, post
from pydantic import BaseModel

from guess_explainr import state
from guess_explainr.model_provider import ModelProvider


class _GetModelsResponse(BaseModel):
    models: list[str]
    error: str | None = None


@get("/models")
async def get_models(provider: str = "openai", api_key: str = "") -> _GetModelsResponse:
    if not api_key:
        return _GetModelsResponse(models=[])
    try:
        models = await ModelProvider(provider).load_model_list(api_key)
    except Exception:
        return _GetModelsResponse(models=[], error="Could not load models — check your API key")
    return _GetModelsResponse(models=models)


class _GetConfigResponse(BaseModel):
    configured: bool


@get("/config")
async def get_config() -> _GetConfigResponse:
    return _GetConfigResponse(configured=state.get_config().ai_provider is not None)


class _SaveConfigRequest(BaseModel):
    provider: str
    model: str
    api_key: str
    maps_api_key: str = ""


class _SaveConfigResponse(BaseModel):
    success: bool


@post("/config")
async def save_config(data: _SaveConfigRequest) -> _SaveConfigResponse:
    with state.modify_config() as config:
        config.ai_provider = ModelProvider(data.provider)
        config.ai_model = data.model
        config.api_key = data.api_key
        config.maps_api_key = data.maps_api_key or None
    return _SaveConfigResponse(success=True)
