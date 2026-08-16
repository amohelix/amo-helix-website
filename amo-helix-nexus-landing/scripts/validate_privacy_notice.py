#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NOTICE = ROOT / "privacy" / "index.html"
HOME = ROOT / "index.html"
REDIRECTS = ROOT / "_redirects"


class NoticeParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.attrs: list[tuple[str, dict[str, str]]] = []
        self.links: list[str] = []
        self.text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key: value or "" for key, value in attrs}
        self.attrs.append((tag, values))
        if tag in {"a", "link", "img", "script"}:
            target = values.get("href") or values.get("src")
            if target:
                self.links.append(target)

    def handle_data(self, data: str) -> None:
        self.text.append(data)


def validate_notice(html: str, home: str, redirects: str, root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    parser = NoticeParser()
    parser.feed(html)
    visible = " ".join(" ".join(parser.text).split())
    lowered = visible.lower()

    required_text = [
        "AMO Helix TestFlight Pilot Privacy Notice",
        "private U.S. TestFlight pilot",
        "synthetic staging",
        "Do not enter real customer data",
        "Reviewer account information",
        "Device, diagnostic, and security records",
        "Synthetic work and history",
        "Audio, photos, and resulting transcripts",
        "service providers",
        "authenticated access",
        "HTTPS connections",
        "Retention can vary",
        "does not currently promise a self-service export or complete deletion workflow",
        "Kevin@amohelix.com",
    ]
    for phrase in required_text:
        if phrase not in visible:
            errors.append(f"missing required text: {phrase}")

    forbidden = {
        "placeholder": r"\bplaceholder\b",
        "draft label": r"\b(?:draft|tbd|todo|lorem ipsum)\b",
        "counsel approval": r"\b(?:counsel|lawyer|attorney)[ -]approved\b",
        "compliance claim": r"\b(?:gdpr|ccpa|hipaa|lgpd)[ -]compliant\b",
        "certification claim": r"\b(?:soc 2|iso 27001)[ -]certified\b",
        "residency claim": r"\bdata (?:never leaves|stays in|is stored only in)\b",
        "no-third-party claim": r"\b(?:no third parties|never share|do not share with service providers)\b",
        "fixed retention": r"\b(?:retain|retained|delete|deleted)\b[^.]{0,80}\b\d+\s+(?:days?|months?|years?)\b",
        "production customer scope": r"\b(?:production customer|customer pilot privacy notice|real-data pilot)\b",
    }
    for label, pattern in forbidden.items():
        if re.search(pattern, lowered, re.IGNORECASE):
            errors.append(f"forbidden {label}")

    html_attrs = [attrs for tag, attrs in parser.attrs if tag == "html"]
    if not html_attrs or html_attrs[0].get("data-privacy-notice") != "testflight-synthetic-staging":
        errors.append("missing exact synthetic-staging document marker")

    canonical = [
        attrs.get("href")
        for tag, attrs in parser.attrs
        if tag == "link" and attrs.get("rel") == "canonical"
    ]
    if canonical != ["https://amohelix.com/privacy"]:
        errors.append("canonical URL must be exactly https://amohelix.com/privacy")

    if any(tag in {"script", "form"} for tag, _ in parser.attrs):
        errors.append("notice must not contain scripts or forms")
    tracking_tokens = ("analytics", "gtag", "segment", "mixpanel", "posthog", "pixel", "tracker")
    linked_resources = " ".join(parser.links).lower()
    if any(token in linked_resources for token in tracking_tokens):
        errors.append("tracking or analytics token found")

    allowed_external = {"https://amohelix.com/privacy", "mailto:Kevin@amohelix.com"}
    for link in parser.links:
        if link.startswith(("http://", "https://", "mailto:")):
            if link not in allowed_external:
                errors.append(f"unapproved external link: {link}")
            continue
        path = link.split("?", 1)[0].split("#", 1)[0]
        if not path or path in {"/", "/privacy"}:
            continue
        local = root / path.lstrip("/")
        if not local.exists():
            errors.append(f"broken local link: {link}")

    if 'href="/privacy"' not in home:
        errors.append("homepage footer does not link to canonical privacy route")
    if "data-privacy-notice=" in home:
        errors.append("homepage must not masquerade as privacy notice")

    exact_redirects = {
        "/privacy /privacy/index.html 200",
        "/privacy/ /privacy/index.html 200",
        "/privacy-policy /privacy 301",
        "/privacy-policy/ /privacy 301",
    }
    actual_redirects = {line.strip() for line in redirects.splitlines() if line.strip()}
    if actual_redirects != exact_redirects:
        errors.append("route contract differs from the four approved privacy mappings")

    return errors


def main() -> int:
    errors = validate_notice(
        NOTICE.read_text(encoding="utf-8"),
        HOME.read_text(encoding="utf-8"),
        REDIRECTS.read_text(encoding="utf-8"),
    )
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    print("PASS: privacy notice content, links, scope, and routes are publication-ready")
    return 0


if __name__ == "__main__":
    sys.exit(main())
