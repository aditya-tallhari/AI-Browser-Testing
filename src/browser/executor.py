from dataclasses import dataclass
from pathlib import Path
import time

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from src.browser.locator_engine import LocatorEngine, LocatorError
from src.models.test_plan import Action, TestPlan, TestStep


class ExecutionError(RuntimeError):
    pass


@dataclass(frozen=True)
class StepResult:
    number: int
    description: str
    passed: bool
    error: str | None = None


class BrowserExecutor:
    def __init__(self, page: Page, username: str | None, password: str | None) -> None:
        self.page = page
        self.username = username
        self.password = password
        self.locators = LocatorEngine(page)

    def execute(self, plan: TestPlan, screenshot_dir: str | Path | None = None) -> list[StepResult]:
        results: list[StepResult] = []
        for number, step in enumerate(plan.steps, start=1):
            try:
                self._run_step(step)
                results.append(StepResult(number, self._describe(step), True))
            except (ExecutionError, LocatorError, PlaywrightTimeoutError) as exc:
                screenshot = self._capture_failure(screenshot_dir, number)
                message = str(exc)
                if screenshot:
                    message = f"{message}; screenshot: {screenshot}"
                results.append(StepResult(number, self._describe(step), False, message))
                break
        return results

    def _run_step(self, step: TestStep) -> None:
        if step.action == Action.NAVIGATE:
            self.page.goto(step.value or step.target or "", wait_until="domcontentloaded", timeout=step.timeout_ms)
        elif step.action == Action.CLICK:
            self._dismiss_non_destructive_overlay(step.timeout_ms)
            self.locators.locate(step.target or "").click(timeout=step.timeout_ms)
        elif step.action == Action.FILL:
            value = self.username if step.value_source == "username" else self.password if step.value_source == "password" else step.value
            if value is None:
                raise ExecutionError(f"Missing credential for {step.value_source}")
            self.locators.locate(step.target or "").fill(value, timeout=step.timeout_ms)
        elif step.action == Action.SELECT_OPTION:
            self.locators.locate(step.target or "").select_option(label=step.value, timeout=step.timeout_ms)
        elif step.action in {Action.CHECK, Action.UNCHECK}:
            locator = self.locators.locate(step.target or "")
            locator.check(timeout=step.timeout_ms) if step.action == Action.CHECK else locator.uncheck(timeout=step.timeout_ms)
        elif step.action == Action.WAIT_FOR_ELEMENT:
            self._wait_for_target(step.target or "", step.timeout_ms)
        elif step.action == Action.ASSERT_VISIBLE:
            self._wait_for_target(step.target or "", step.timeout_ms)
        elif step.action == Action.ASSERT_TEXT:
            if step.value is None:
                raise ExecutionError("assert_text requires value")
            self.locators.locate(step.target or "").wait_for(state="visible", timeout=step.timeout_ms)
            actual = self.locators.locate(step.target or "").inner_text()
            if step.value.lower() not in actual.lower():
                raise ExecutionError(f"Expected text '{step.value}', actual text was '{actual}'")
        elif step.action == Action.ASSERT_URL:
            self.page.wait_for_url(step.target or "", timeout=step.timeout_ms)
        elif step.action == Action.ASSERT_TITLE:
            if step.value is None:
                raise ExecutionError("assert_title requires value")
            self.page.wait_for_function(
                "(expected) => document.title.trim().toLowerCase() === expected.trim().toLowerCase()",
                arg=step.value,
                timeout=step.timeout_ms,
            )
            actual_title = self.page.title()
            if actual_title.strip().casefold() != step.value.strip().casefold():
                raise ExecutionError(f"Expected title '{step.value}', actual title was '{actual_title}'")
        else:
            raise ExecutionError(f"Unsupported action: {step.action}")

    def _dismiss_non_destructive_overlay(self, timeout_ms: int) -> None:
        overlays = self.page.locator("[role='dialog'], .modal-overlay, [aria-modal='true']")
        for index in range(overlays.count()):
            overlay = overlays.nth(index)
            if not overlay.is_visible():
                continue
            for label in ("I Understand & Continue", "Continue", "Accept", "Close"):
                button = overlay.get_by_role("button", name=label, exact=True)
                if button.count() == 1 and button.is_visible() and button.is_enabled():
                    button.click(timeout=timeout_ms)
                    return

    def _wait_for_target(self, target: str, timeout_ms: int) -> None:
        deadline = time.monotonic() + timeout_ms / 1000
        last_error: LocatorError | None = None
        while time.monotonic() < deadline:
            try:
                locator = self.locators.locate(target)
                locator.wait_for(state="visible", timeout=min(500, timeout_ms))
                return
            except (LocatorError, PlaywrightTimeoutError) as exc:
                if isinstance(exc, LocatorError):
                    last_error = exc
                self.page.wait_for_timeout(200)
        if last_error:
            raise last_error
        raise ExecutionError(f"Timed out waiting for '{target}'")

    def _capture_failure(self, directory: str | Path | None, number: int) -> str | None:
        if not directory:
            return None
        path = Path(directory)
        path.mkdir(parents=True, exist_ok=True)
        screenshot = path / f"step-{number}.png"
        self.page.screenshot(path=str(screenshot), full_page=True)
        return str(screenshot)

    @staticmethod
    def _describe(step: TestStep) -> str:
        return f"{step.action.value}: {step.target or step.value or ''}"
