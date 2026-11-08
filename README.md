# AI Browser Testing

## Overview

This project converts a plain-English test case into a validated browser test plan, then executes only approved Playwright actions. It is a reusable tool rather than a hardcoded PHPTravels script.

Flow:

```text
Plain English -> OpenAI-compatible planner -> Pydantic TestPlan -> Playwright -> assertions -> JSON report
```

## Requirements

- Python 3.11 or newer
- Google Chrome is recommended for Chromium execution
- A Groq API key

## Installation

```powershell
cd AI-Browser-Testing
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m playwright install chromium
Copy-Item .env.example .env
```

Set your provider key and endpoint in `.env`. OpenRouter is supported with `OPENROUTER_API_KEY` and `https://openrouter.ai/api/v1`; Groq is supported with `GROQ_API_KEY` and `https://api.groq.com/openai/v1`. Never commit `.env`; it is ignored by Git.

For compatibility, an existing key stored as `OPENROUTER_API_KEY` is also accepted when it is a Groq key. If the key starts with `gsk_`, the application automatically uses `https://api.groq.com/openai/v1`, even if an old OpenRouter base URL remains in `.env`.

## Run

```powershell
python -m src.main `
  --url "https://example.com" `
  --test "Open the site and verify that the welcome heading is visible"
```

Useful options:

- `--username` and `--password`: runtime credentials; environment variables `DEFAULT_USERNAME` and `DEFAULT_PASSWORD` are also supported.
- `--headed`: show the browser. The default is headless.
- `--browser chromium|firefox|webkit`
- `--model`: provider model override.
- `--reports-dir`: JSON report and failure screenshots directory.

## PHPTravels example

Use the currently supplied PHPTravels URL and valid credentials at runtime; credentials are deliberately not invented or stored in source:

```powershell
python -m src.main `
  --url "https://your-phptravels-url.example" `
  --username "$env:PHPTRAVELS_USERNAME" `
  --password "$env:PHPTRAVELS_PASSWORD" `
  --test "Log in as a customer and verify that the customer dashboard is shown"
```

The core engine has no PHPTravels selectors. The AI describes intent, and the locator engine uses roles, labels, placeholders, and visible text.

## Architecture

- `src/models/test_plan.py`: closed list of supported actions and validation rules.
- `src/ai/planner.py`: OpenAI-compatible Groq client and safe JSON-to-Pydantic conversion.
- `src/ai/prompts.py`: planner contract and prompt construction.
- `src/browser/locator_engine.py`: semantic locator resolution and ambiguity errors.
- `src/browser/executor.py`: approved action execution, assertions, step results, consent-overlay handling, and failure screenshots.
- `src/browser/browser_manager.py`: Playwright lifecycle management.
- `src/reporting/reporter.py`: readable console output and timestamped JSON reports.
- `src/utils/config.py`: environment and CLI validation.

## Supported actions

`navigate`, `click`, `fill`, `select_option`, `check`, `uncheck`, `wait_for_element`, `assert_visible`, `assert_text`, `assert_url`, and `assert_title`.

AI output is never executed as code. Unknown actions, extra fields, malformed JSON, missing required arguments, and unsupported destructive behavior are rejected or fail safely.

Field locators score visible enabled controls using type, labels, placeholders, autocomplete, nearby form text, and form context. For example, when a page has both a login email and a newsletter email, a login-form candidate outranks a subscription-form candidate. Equal candidates produce a diagnostic ambiguity error instead of a random selection.

## Tests

Unit tests use fake AI responses and mocks, so they do not consume API credits or require a browser:

```powershell
pytest
```

The live PHPTravels workflow cannot be claimed as executed without a currently reachable URL and valid credentials. The command above is the supported manual validation path.

## Reports and failures

Each run writes a timestamped JSON report under `reports/`. Reports preserve the original test-case string exactly and distinguish AI planning, browser execution, assertions, and overall result. If browser execution reaches a step failure, a screenshot is captured there. Reports never include API keys, and password values are not printed.

## Limitations

Semantic locators cannot guarantee success on pages with no accessible names, intentionally misleading labels, cross-origin frames, Shadow DOM controls, CAPTCHAs, or custom widgets. The planner is probabilistic and requires a valid API response. Ambiguous matches stop execution rather than randomly clicking. The current safety prompt and action allowlist are not a replacement for human review of high-impact workflows.

## Adding a new test

No source change is required: provide a new `--test` sentence and the target URL. If the site exposes good accessibility semantics, the same locator engine can resolve the new targets. Add a new action to the Pydantic enum, executor, prompt, and tests only when a genuinely new browser capability is needed.
