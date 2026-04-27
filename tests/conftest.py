import pytest

from guess_explainr import state


@pytest.fixture(autouse=True)
def reset_panorama_state():
    state.panorama_state.panorama_id = None
    state.panorama_state.panorama_image_bytes = None
    yield
    state.panorama_state.panorama_id = None
    state.panorama_state.panorama_image_bytes = None
