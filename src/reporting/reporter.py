import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.browser.executor import StepResult


def write_report(
    directory: str,
    url: str,
    test_case: str,
    plan_status: str,
    results: list[StepResult],
    error: str | None = None,
) -> Path:
    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc)
    report: dict[str, Any] = {
        "timestamp_utc": timestamp.isoformat(),
        "website": url,
        "test_case": test_case,
        "ai_planning": plan_status,
        "browser_execution": "PASS" if results and all(item.passed for item in results) else "FAIL",
        "assertions": (
            "PASS"
            if results and all(item.passed for item in results)
            else "FAIL"
        ),
        "overall_result": "PASS" if plan_status == "PASS" and results and all(item.passed for item in results) else "FAIL",
        "steps": [asdict(item) for item in results],
        "error": error,
    }
    report_path = path / f"run-{timestamp.strftime('%Y%m%dT%H%M%SZ')}.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print_report(report)
    return report_path


def print_report(report: dict[str, Any]) -> None:
    print("\nAI BROWSER TEST REPORT\n")
    print(f"Website: {report['website']}")
    print(f"Test Case: {report['test_case']}\n")
    print(f"AI Planning: {report['ai_planning']}")
    print(f"Browser Execution: {report['browser_execution']}")
    print(f"Assertions: {report['assertions']}")
    for step in report["steps"]:
        status = "PASS" if step["passed"] else "FAIL"
        suffix = f" — {step['error']}" if step["error"] else ""
        print(f"Step {step['number']}: {step['description']} — {status}{suffix}")
    if report["error"]:
        print(f"Error: {report['error']}")
    print(f"\nOverall Result: {report['overall_result']}")
