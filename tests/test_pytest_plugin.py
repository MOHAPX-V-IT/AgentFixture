def test_plugin_fixtures(agent_recorder, agent_replay, assert_agent_trace):
    agent_recorder.call("search", {"id": 1}, lambda id: {"id": id})
    assert_agent_trace(agent_recorder.calls, {"counts": {"search": 1}})
    replay = agent_replay(agent_recorder.calls)
    assert replay.call("search", {"id": 1}) == {"id": 1}
    replay.assert_consumed()
