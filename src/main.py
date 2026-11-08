import argparse
import os
import sys

from src.ai.planner import OpenAICompatibleClient, PlannerError, TestPlanner
from src.browser.browser_manager import open_page
from src.browser.executor import BrowserExecutor
from src.reporting.reporter import write_report
from src.utils.config import ConfigurationError, Settings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert plain-English tests into safe browser actions.")
    parser.add_argument("--url", required=True)
    parser.add_argument("--test", dest="test_case", required=True)
    parser.add_argument("--username", default=os.getenv("DEFAULT_USERNAME"))
    parser.add_argument("--password", default=os.getenv("DEFAULT_PASSWORD"))
    api_key = os.getenv("GROQ_API_KEY") or os.getenv("OPENROUTER_API_KEY")
    configured_base_url = os.getenv("AI_BASE_URL")
    default_base_url = (
        "https://api.groq.com/openai/v1"
        if not configured_base_url or (api_key or "").startswith("gsk_")
        else configured_base_url
    )
    parser.add_argument("--model", default=os.getenv("AI_MODEL", "openai/gpt-oss-20b"))
    parser.add_argument("--base-url", default=default_base_url)
    parser.add_argument("--api-key", default=api_key)
    parser.add_argument("--browser", choices=["chromium", "firefox", "webkit"], default="chromium")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--reports-dir", default="reports")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    settings = Settings(
        args.url, args.test_case, args.username, args.password, args.model,
        args.base_url, args.api_key, not args.headed, args.browser, args.reports_dir,
    )
    try:
        settings.validate()
        if not settings.api_key:
            raise ConfigurationError("GROQ_API_KEY is required for AI planning")
        plan = TestPlanner(OpenAICompatibleClient(settings.api_key, settings.model, settings.base_url)).create_plan(
            settings.url, settings.test_case
        )
    except (ConfigurationError, PlannerError) as exc:
        write_report(settings.reports_dir, settings.url, settings.test_case, "FAIL", [], str(exc))
        return 2

    try:
        with open_page(settings.browser, settings.headless) as page:
            results = BrowserExecutor(page, settings.username, settings.password).execute(plan, settings.reports_dir)
        write_report(settings.reports_dir, settings.url, settings.test_case, "PASS", results)
        return 0 if results and all(result.passed for result in results) else 1
    except Exception as exc:
        write_report(settings.reports_dir, settings.url, settings.test_case, "PASS", [], str(exc))
        return 1


if __name__ == "__main__":
    sys.exit(main())
