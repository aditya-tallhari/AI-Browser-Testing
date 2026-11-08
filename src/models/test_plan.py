from enum import Enum
from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator, model_validator


class Action(str, Enum):
    NAVIGATE = "navigate"
    CLICK = "click"
    FILL = "fill"
    SELECT_OPTION = "select_option"
    CHECK = "check"
    UNCHECK = "uncheck"
    WAIT_FOR_ELEMENT = "wait_for_element"
    ASSERT_VISIBLE = "assert_visible"
    ASSERT_TEXT = "assert_text"
    ASSERT_URL = "assert_url"
    ASSERT_TITLE = "assert_title"


class TestStep(BaseModel):
    __test__ = False
    model_config = ConfigDict(extra="forbid")

    action: Action
    target: str | None = None
    value: str | None = Field(default=None, validation_alias=AliasChoices("value", "expected"))
    value_source: Literal["username", "password"] | None = None
    timeout_ms: int = Field(default=10_000, ge=500, le=120_000)

    @field_validator("target", "value", "value_source", mode="before")
    @classmethod
    def empty_strings_are_missing(cls, value: str | None) -> str | None:
        return None if isinstance(value, str) and not value.strip() else value

    @model_validator(mode="after")
    def validate_arguments(self) -> "TestStep":
        if self.action == Action.NAVIGATE:
            if not self.value and not self.target:
                raise ValueError("navigate requires a URL in value or target")
        elif self.action in {Action.FILL, Action.SELECT_OPTION}:
            if not self.target or (not self.value and not self.value_source):
                raise ValueError(f"{self.action.value} requires target and value/value_source")
        elif self.action in {
            Action.CLICK, Action.CHECK, Action.UNCHECK, Action.WAIT_FOR_ELEMENT,
            Action.ASSERT_VISIBLE, Action.ASSERT_TEXT, Action.ASSERT_URL,
        } and not self.target:
            raise ValueError(f"{self.action.value} requires target")
        elif self.action == Action.ASSERT_TITLE and not self.value:
            raise ValueError("assert_title requires value")
        if self.value_source and self.action != Action.FILL:
            raise ValueError("value_source is only valid for fill")
        return self


class TestPlan(BaseModel):
    __test__ = False
    model_config = ConfigDict(extra="forbid")

    goal: str = Field(min_length=1)
    steps: list[TestStep] = Field(min_length=1, max_length=50)
