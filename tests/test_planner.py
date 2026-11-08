import pytest

from src.ai.planner import PlannerError, TestPlanner


class FakeClient:
    def __init__(self, response: str):
        self.response = response

    def create(self, system_prompt: str, user_prompt: str) -> str:
        return self.response


def test_planner_parses_valid_plan():
    planner = TestPlanner(FakeClient('{"goal":"Check login","steps":[{"action":"navigate","value":"https://example.com"},{"action":"assert_visible","target":"Login button"}]}'))
    plan = planner.create_plan("https://example.com", "Check login")
    assert plan.goal == "Check login"
    assert len(plan.steps) == 2


def test_planner_rejects_invalid_json():
    with pytest.raises(PlannerError, match="invalid test plan"):
        TestPlanner(FakeClient("not json")).create_plan("https://example.com", "Check login")


def test_planner_rejects_unsupported_action():
    response = '{"goal":"bad","steps":[{"action":"execute_code","target":"anything"}]}'
    with pytest.raises(PlannerError, match="invalid test plan"):
        TestPlanner(FakeClient(response)).create_plan("https://example.com", "bad")


def test_planner_requires_inputs():
    with pytest.raises(PlannerError):
        TestPlanner(FakeClient("{}")).create_plan("", "")
