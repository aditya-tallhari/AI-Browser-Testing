from unittest.mock import Mock

import pytest

from src.browser.executor import BrowserExecutor
from src.models.test_plan import TestPlan


class TitlePage:
    def __init__(self, title: str = "Example Domain") -> None:
        self._title = title
        self.wait_call = None

    def wait_for_function(self, expression, *, arg, timeout):
        self.wait_call = (expression, arg, timeout)

    def title(self):
        return self._title


def test_missing_password_fails_without_browser_action():
    page = Mock()
    plan = TestPlan.model_validate({
        "goal": "login",
        "steps": [{"action": "fill", "target": "password field", "value_source": "password"}],
    })
    results = BrowserExecutor(page, "user@example.com", None).execute(plan)
    assert results[0].passed is False
    assert "Missing credential" in results[0].error


def test_invalid_action_is_rejected_by_model():
    with pytest.raises(ValueError):
        TestPlan.model_validate({"goal": "bad", "steps": [{"action": "run_shell", "target": "x"}]})


def test_assert_title_uses_keyword_argument_and_verifies_title():
    page = TitlePage()
    plan = TestPlan.model_validate({
        "goal": "title",
        "steps": [{"action": "assert_title", "value": "Example Domain"}],
    })
    results = BrowserExecutor(page, None, None).execute(plan)
    assert results[0].passed
    assert page.wait_call[1] == "Example Domain"


def test_failed_title_assertion_is_reported():
    page = TitlePage("Wrong Title")
    plan = TestPlan.model_validate({
        "goal": "title",
        "steps": [{"action": "assert_title", "value": "Example Domain"}],
    })
    results = BrowserExecutor(page, None, None).execute(plan)
    assert not results[0].passed
    assert "actual title was 'Wrong Title'" in results[0].error


def test_assert_title_accepts_expected_field_from_ai_plan():
    plan = TestPlan.model_validate({
        "goal": "title",
        "steps": [{"action": "assert_title", "target": "page title", "expected": "Example Domain"}],
    })
    assert plan.steps[0].value == "Example Domain"
