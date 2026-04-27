import dataclasses
import textwrap
from collections.abc import AsyncGenerator

from pydantic_ai import Agent, BinaryContent, RunContext

from guess_explainr import state
from guess_explainr.plonkit_cache import get_plonkit_dir


@dataclasses.dataclass(frozen=True)
class AgentDependency:
    compare_country_ids: list[str]
    user_questions: str


def _make_agent() -> Agent[AgentDependency]:
    state_config = state.get_config()
    prompt = textwrap.dedent("""
        You are an experienced teacher of the game GeoGuessr.
        You will be provided an image of a Google Street View location and a task to explain t
        the user,so that they can learn to become better at the game from it.

        You will also be provided with a set of relevant guides.
        These explain clues that might be used by players of the game t
        distinguish locations from another.
        Base all your analysis and explanations on content provided by these guides.\
        Output your response in plain text or Markdown formatting.
        Never begin with greetings, thanks, or preambles. Start with substantive content. No sign-offs or apologies. Do not mention being a model.\
        """)  # noqa: E501

    assert state_config.ai_provider is not None
    _, model = state_config.ai_provider.to_pydantic(
        model_name=state_config.ai_model or "", api_key=state_config.api_key or ""
    )

    agent = Agent(
        model,
        deps_type=AgentDependency,
        instructions=prompt,
    )

    @agent.instructions
    def task(ctx: RunContext[AgentDependency]) -> str:
        return (
            f"You will be given guides for the following countries: "
            f"{ctx.deps.compare_country_ids}. "
            f"Only consider these as options for where the location might be. "
            f"The user also asked: {ctx.deps.user_questions}"
        )

    return agent


def _load_plonkit_guide(country_id: str) -> BinaryContent:
    filename = get_plonkit_dir() / f"{country_id}.pdf"
    return BinaryContent(data=filename.read_bytes(), media_type="application/pdf")


def _load_panorama_image() -> BinaryContent:
    image_bytes = state.panorama_state.panorama_image_bytes
    if not image_bytes:
        raise ValueError("Panorama image not available in state")
    return BinaryContent(data=image_bytes, media_type="image/jpeg")


async def stream_analysis(
    compare_country_ids: list[str],
    user_questions: str,
    *,
    only_delta: bool,
) -> AsyncGenerator[str, None]:
    agent = _make_agent()
    guides = [_load_plonkit_guide(country_id) for country_id in compare_country_ids]
    image_prompt = [
        "This is the Street View panorama image that you are supposed to analyze:",
        _load_panorama_image(),
    ]
    async with agent.run_stream(
        user_prompt=image_prompt + guides,
        deps=AgentDependency(
            compare_country_ids=compare_country_ids, user_questions=user_questions
        ),
    ) as result:
        async for text in result.stream_text(delta=only_delta):
            yield text
