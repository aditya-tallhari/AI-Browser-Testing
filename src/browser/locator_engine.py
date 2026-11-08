import re

from playwright.sync_api import Locator, Page


class LocatorError(RuntimeError):
    pass


class LocatorEngine:
    def __init__(self, page: Page) -> None:
        self.page = page

    def locate(self, description: str) -> Locator:
        text = description.strip()
        if not text:
            raise LocatorError("Cannot locate an empty target")

        if self._is_field_target(text):
            return self._locate_field(text)

        candidates = [self.page.get_by_role("button", name=text, exact=True)]
        if "button" not in text.casefold():
            candidates.append(self.page.get_by_role("link", name=text, exact=True))
        candidates.extend([
            self.page.get_by_label(text, exact=True),
            self.page.get_by_placeholder(text, exact=True),
            self.page.get_by_text(text, exact=True),
        ])
        for candidate in candidates:
            count = candidate.count()
            if count == 1:
                if candidate.is_visible() and candidate.is_enabled():
                    return candidate
                continue
            if count > 1:
                raise LocatorError(f"Ambiguous target '{description}': {count} elements matched")

        for alias in self._intent_aliases(text):
            roles = ("button",) if "button" in text.casefold() else ("button", "link")
            for role in roles:
                candidate = self.page.get_by_role(role, name=alias, exact=True)
                count = candidate.count()
                if count == 1:
                    if candidate.is_visible() and candidate.is_enabled():
                        return candidate
                    continue
                if count > 1:
                    continue

        semantic = self._semantic_fallback(text)
        if semantic.count() == 1:
            return semantic
        if semantic.count() > 1:
            raise LocatorError(f"Ambiguous target '{description}': {semantic.count()} elements matched")
        raise LocatorError(f"Could not locate '{description}' using semantic locators")

    def _locate_field(self, description: str) -> Locator:
        lowered = description.casefold()
        inputs = self.page.locator("input, textarea, select")
        scored: list[tuple[int, Locator, str]] = []
        for index in range(inputs.count()):
            candidate = inputs.nth(index)
            if not candidate.is_visible() or not candidate.is_enabled():
                continue
            score, context = self._score_field(candidate, lowered)
            if score > 0:
                scored.append((score, candidate, context))

        if not scored:
            raise LocatorError(
                f"Could not locate '{description}'. No visible enabled field matched its semantic meaning."
            )

        scored.sort(key=lambda item: item[0], reverse=True)
        if len(scored) > 1 and scored[0][0] - scored[1][0] < 15:
            details = "; ".join(
                self._field_diagnostic(item[1], item[2]) for item in scored[:5]
            )
            raise LocatorError(
                f"Ambiguous target '{description}': {len(scored)} matching visible fields. {details}"
            )
        return scored[0][1]

    def _score_field(self, field: Locator, target: str) -> tuple[int, str]:
        attributes = {
            name: field.get_attribute(name) or ""
            for name in ("type", "id", "name", "placeholder", "aria-label", "autocomplete", "form")
        }
        form = field.locator("xpath=ancestor::form[1]")
        form_context = ""
        if form.count():
            form_context = " ".join(
                filter(None, [
                    form.get_attribute("id") or "",
                    form.get_attribute("class") or "",
                    form.get_attribute("action") or "",
                    form.inner_text(),
                ])
            )
        searchable = self._normalize(
            " ".join([*attributes.values(), field.get_attribute("title") or "", form_context])
        )
        score = 0
        if "email" in target:
            if attributes["type"].casefold() == "email":
                score += 60
            if "email" in self._normalize(attributes["name"]):
                score += 25
            if "email" in self._normalize(attributes["placeholder"]):
                score += 25
            if self._normalize(attributes["autocomplete"]) == "email":
                score += 20
        elif "password" in target:
            if attributes["type"].casefold() == "password":
                score += 70
            if "password" in searchable:
                score += 25
        elif "username" in target or "user name" in target:
            if attributes["type"].casefold() in {"text", "email"}:
                score += 20
            if any(term in searchable for term in ("username", "user name", "email")):
                score += 35
        else:
            if any(term in searchable for term in target.split()):
                score += 20

        if any(term in searchable for term in ("login", "sign in", "log in", "authentication")):
            score += 45
        if any(term in searchable for term in ("newsletter", "subscribe", "travel deals")):
            score -= 45
        if attributes["type"].casefold() in {"hidden", "submit", "button"}:
            score = 0
        return score, form_context

    def _field_diagnostic(self, field: Locator, form_context: str) -> str:
        details = " ".join(
            f"{name}='{field.get_attribute(name) or ''}'"
            for name in ("type", "id", "name", "placeholder", "aria-label")
        )
        return f"[{details} visible={field.is_visible()} enabled={field.is_enabled()} form='{self._normalize(form_context)[:100]}']"

    @staticmethod
    def _is_field_target(description: str) -> bool:
        lowered = description.casefold()
        return any(term in lowered for term in ("email", "password", "username", "user name", "field", "input"))

    def _semantic_fallback(self, text: str) -> Locator:
        aliases = self._intent_aliases(text)
        controls = self.page.locator(
            "button, input[type='submit'], input[type='button'], [role='button'], a"
        )
        scored: list[tuple[int, Locator, str]] = []
        for index in range(controls.count()):
            control = controls.nth(index)
            if not control.is_visible() or not control.is_enabled():
                continue
            searchable = " ".join(
                filter(
                    None,
                    [
                        control.inner_text(),
                        control.get_attribute("aria-label"),
                        control.get_attribute("title"),
                        control.get_attribute("value"),
                    ],
                )
            ).strip()
            normalized = self._normalize(searchable)
            score = max(
                (100 if normalized == self._normalize(alias) else 70 if self._normalize(alias) in normalized else 0)
                for alias in aliases
            )
            form = control.locator("xpath=ancestor::form[1]")
            form_context = ""
            if form.count():
                form_context = self._normalize(" ".join(filter(None, [
                    form.get_attribute("id") or "",
                    form.get_attribute("class") or "",
                    form.get_attribute("action") or "",
                    form.inner_text(),
                ])))
                if any(term in form_context for term in ("login", "sign in", "authentication")):
                    score += 40
            if score:
                scored.append((score, control, f"{searchable} form='{form_context[:100]}'"))

        if scored:
            scored.sort(key=lambda item: item[0], reverse=True)
            if len(scored) > 1 and scored[0][0] == scored[1][0]:
                raise LocatorError(
                    f"Ambiguous target '{text}': candidates '{scored[0][2]}' and '{scored[1][2]}'"
                )
            return scored[0][1]

        lowered = text.lower()
        if "email" in lowered:
            return self.page.locator("input[type='email']")
        if "password" in lowered:
            return self.page.locator("input[type='password']")
        return self._locate_text_target(text)

    def _locate_text_target(self, description: str) -> Locator:
        target_words = {
            word for word in self._normalize(description).split()
            if word not in {"page", "element", "section", "area", "customer"}
        }
        headings = self.page.locator("h1, h2, h3, h4, [role='heading']")
        scored: list[tuple[int, Locator, str]] = []
        for index in range(headings.count()):
            heading = headings.nth(index)
            if not heading.is_visible():
                continue
            text = self._normalize(heading.inner_text())
            matched = sum(word in text for word in target_words)
            if matched:
                scored.append((matched * 100 - len(text), heading, text))

        if scored:
            scored.sort(key=lambda item: item[0], reverse=True)
            if len(scored) > 1 and scored[0][0] == scored[1][0]:
                raise LocatorError(
                    f"Ambiguous target '{description}': headings '{scored[0][2]}' and '{scored[1][2]}'"
                )
            return scored[0][1]

        return self.page.get_by_text(description, exact=False)

    @staticmethod
    def _intent_aliases(description: str) -> list[str]:
        lowered = description.casefold()
        aliases: list[str] = [description]
        if any(term in lowered for term in ("login", "log in", "sign in")):
            aliases.extend(["Login", "Log in", "Sign in", "Submit"])
        if "button" in lowered:
            aliases.append(description.replace("button", "").strip())
        return list(dict.fromkeys(alias for alias in aliases if alias))

    @staticmethod
    def _normalize(value: str) -> str:
        return re.sub(r"\s+", " ", value).strip().casefold()
