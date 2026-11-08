import json
from typing import Any, Protocol
from urllib import error, request

from pydantic import ValidationError

from src.ai.prompts import SYSTEM_PROMPT, build_user_prompt
from src.models.test_plan import TestPlan


class PlannerError(RuntimeError):
    pass


class ChatClient(Protocol):
    def create(self, system_prompt: str, user_prompt: str) -> str:
        ...


class OpenAICompatibleClient:
    def __init__(self, api_key: str, model: str, base_url: str) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")

    def create(self, system_prompt: str, user_prompt: str) -> str:
        payload = json.dumps({
            "model": self.model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }).encode()
        http_request = request.Request(
            f"{self.base_url}/chat/completions",
            data=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with request.urlopen(http_request, timeout=60) as response:
                body: Any = json.loads(response.read().decode())
        except error.HTTPError as exc:
            try:
                details = exc.read().decode("utf-8", errors="replace")
            except Exception:
                details = "No response details available"
            raise PlannerError(f"AI request failed with HTTP {exc.code}: {details[:500]}") from exc
        except (error.URLError, TimeoutError) as exc:
            raise PlannerError(f"AI request failed: {exc}") from exc
        try:
            return body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise PlannerError("AI response did not contain message content") from exc


OpenRouterClient = OpenAICompatibleClient


class TestPlanner:
    __test__ = False

    def __init__(self, client: ChatClient) -> None:
        self.client = client

    def create_plan(self, url: str, test_case: str) -> TestPlan:
        if not url.strip() or not test_case.strip():
            raise PlannerError("URL and test case are required")
        prompt = build_user_prompt(url, test_case)
        last_error: Exception | None = None
        for attempt in range(2):
            raw = self.client.create(SYSTEM_PROMPT, prompt)
            try:
                decoded = json.loads(raw)
                return TestPlan.model_validate(decoded)
            except (json.JSONDecodeError, ValidationError, TypeError) as exc:
                last_error = exc
                prompt = (
                    f"{build_user_prompt(url, test_case)}\n"
                    "Your previous JSON was invalid. Return corrected JSON only. "
                    "Every assert_title step must have a non-empty value."
                )
        raise PlannerError(f"AI returned an invalid test plan after 2 attempts: {last_error}") from last_error
