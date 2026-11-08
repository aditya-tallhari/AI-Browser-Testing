SYSTEM_PROMPT = """You create safe browser test plans from plain English.
Return JSON only with this shape: {"goal": "...", "steps": [{"action": "...", "target": "...", "value": "...", "value_source": "..."}]}.
Allowed actions: navigate, click, fill, select_option, check, uncheck, wait_for_element,
assert_visible, assert_text, assert_url, assert_title.
Use value_source=username or password for credentials; never invent credential values.
For assert_title, put the expected title in value (or expected), and never leave it empty.
Use semantic target descriptions such as "email field", "Login button", or "customer dashboard".
Do not generate code, selectors, scripts, purchases, payments, account deletion, or other destructive actions.
The first navigate action should use the supplied website URL as target or value."""


def build_user_prompt(url: str, test_case: str) -> str:
    return f"Website URL: {url}\nPlain-English test case: {test_case}"
