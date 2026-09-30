import pytest
from .core import Replay, assert_trace
from .recording import Recorder


@pytest.fixture
def agent_recorder():
    return Recorder()


@pytest.fixture
def agent_replay():
    return Replay


@pytest.fixture
def assert_agent_trace():
    return assert_trace
