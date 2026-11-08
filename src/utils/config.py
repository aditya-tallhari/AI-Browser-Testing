import os
from dataclasses import dataclass
from urllib.parse import urlparse

from dotenv import load_dotenv

load_dotenv()


class ConfigurationError(ValueError):
    pass


@dataclass(frozen=True)
class Settings:
    url: str
    test_case: str
    username: str | None
    password: str | None
    model: str
    base_url: str
    api_key: str | None
    headless: bool
    browser: str
    reports_dir: str

    def validate(self) -> None:
        parsed = urlparse(self.url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ConfigurationError("URL must be an absolute http or https URL")
        if not self.test_case.strip():
            raise ConfigurationError("Test case cannot be empty")
        if self.browser not in {"chromium", "firefox", "webkit"}:
            raise ConfigurationError("Browser must be chromium, firefox, or webkit")
