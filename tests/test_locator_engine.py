import pytest
from playwright.sync_api import sync_playwright

from src.browser.locator_engine import LocatorEngine, LocatorError


class Candidate:
    def __init__(self, count: int, text: str = "Login"):
        self._count = count
        self._text = text

    def count(self):
        return self._count

    def is_visible(self):
        return True

    def is_enabled(self):
        return True

    def inner_text(self):
        return self._text

    def get_attribute(self, name):
        return None

    def locator(self, selector):
        return Candidate(0)

    def nth(self, index):
        return Candidate(1, self._text)


class FakePage:
    def __init__(self, login_count: int = 0):
        self.login_count = login_count

    def get_by_role(self, role, name=None, exact=False):
        return Candidate(self.login_count if role == "button" and name == "Login" else 0)

    def get_by_label(self, text, exact=False):
        return Candidate(0)

    def get_by_placeholder(self, text, exact=False):
        return Candidate(0)

    def get_by_text(self, text, exact=False):
        return Candidate(0)

    def locator(self, selector):
        if selector.startswith("button,"):
            return Candidate(self.login_count)
        return Candidate(0)


def test_login_button_intent_matches_exact_login_name():
    candidate = LocatorEngine(FakePage(login_count=1)).locate("Login button")
    assert candidate.count() == 1


def test_login_button_ambiguity_fails_safely():
    with pytest.raises(LocatorError, match="Ambiguous"):
        LocatorEngine(FakePage(login_count=2)).locate("Login button")


def test_missing_locator_has_meaningful_error():
    with pytest.raises(LocatorError, match="Could not locate"):
        LocatorEngine(FakePage()).locate("Dashboard button")


def test_email_field_prefers_visible_login_form_over_newsletter():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.set_content("""
            <form id="login-form" action="/login">
                <label>Email Address <input type="email" name="email" placeholder="Email Address"></label>
            </form>
            <form action="/newsletter/subscribe">
                <input type="email" name="email" placeholder="Email Address">
            </form>
        """)
        selected = LocatorEngine(page).locate("email field")
        assert selected.get_attribute("name") == "email"
        assert selected.locator("xpath=ancestor::form[1]").get_attribute("id") == "login-form"
        browser.close()


def test_hidden_email_is_ignored():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.set_content("""
            <input type="email" name="email" value="hidden" style="display:none">
            <form id="login-form"><input type="email" name="email" placeholder="Email Address"></form>
        """)
        selected = LocatorEngine(page).locate("email field")
        assert selected.is_visible()
        assert selected.input_value() == ""
        browser.close()


def test_multiple_visible_email_fields_report_contextual_ambiguity():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.set_content("""
            <form><input type="email" name="primary" placeholder="Email Address"></form>
            <form><input type="email" name="secondary" placeholder="Email Address"></form>
        """)
        with pytest.raises(LocatorError, match="matching visible fields"):
            LocatorEngine(page).locate("email field")
        browser.close()
