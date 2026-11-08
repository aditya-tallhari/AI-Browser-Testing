import pytest

from src.utils.config import ConfigurationError, Settings


def test_invalid_url_is_rejected():
    settings = Settings("not-a-url", "check page", None, None, "model", "https://api.example.com", None, True, "chromium", "reports")
    with pytest.raises(ConfigurationError, match="absolute http"):
        settings.validate()


def test_unknown_browser_is_rejected():
    settings = Settings("https://example.com", "check page", None, None, "model", "https://api.example.com", None, True, "safari", "reports")
    with pytest.raises(ConfigurationError, match="Browser"):
        settings.validate()
