import json

from src.reporting.reporter import write_report


def test_report_preserves_original_test_case(tmp_path):
    original = "Open the website and verify that the page title is Example Domain"
    report_path = write_report(str(tmp_path), "https://example.com", original, "PASS", [])
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["test_case"] == original
