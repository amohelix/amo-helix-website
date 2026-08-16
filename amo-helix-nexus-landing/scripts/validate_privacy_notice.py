#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from html.parser import HTMLParser
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from simulate_cloudflare_pages import file_inventory, validate_privacy_routes

ROOT = Path(__file__).resolve().parents[1]
NOTICE = ROOT / "privacy.html"
HOME = ROOT / "index.html"
REDIRECTS = ROOT / "_redirects"
DEPLOYMENT_DOC = ROOT.parent / "docs" / "TESTFLIGHT_PILOT_PRIVACY_NOTICE_DEPLOYMENT.md"

APPROVED_CONTACT = "Kevin@amohelix.com"
APPROVED_CONTACT_LINK = f"mailto:{APPROVED_CONTACT}"
GUARDED_CONTACT = (
    '<!--email_off--><a href="mailto:Kevin@amohelix.com">'
    "Kevin@amohelix.com</a><!--/email_off-->"
)


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


def validate_notice(
    html: str,
    home: str,
    redirects: str,
    root: Path = ROOT,
    *,
    paths: set[str] | None = None,
    project_config: str | None = None,
    readme: str | None = None,
    deployment_doc: str | None = None,
) -> list[str]:
    errors: list[str] = []
    parser = NoticeParser()
    parser.feed(html)
    visible = " ".join(" ".join(parser.text).split())
    lowered = visible.lower()
    inventory = paths if paths is not None else file_inventory(root)
    config_text = project_config if project_config is not None else (root / "wrangler.toml").read_text(encoding="utf-8")
    readme_text = readme if readme is not None else (root / "README.md").read_text(encoding="utf-8")
    doc_text = deployment_doc if deployment_doc is not None else DEPLOYMENT_DOC.read_text(encoding="utf-8")

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
        APPROVED_CONTACT,
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

    if html.count("<!--email_off-->") != 1 or html.count("<!--/email_off-->") != 1:
        errors.append("contact must have exactly one complete email_off guard")
    if html.count(GUARDED_CONTACT) != 1:
        errors.append("approved contact link must be exactly enclosed by email_off guard")
    mailto_links = [link for link in parser.links if link.startswith("mailto:")]
    if mailto_links != [APPROVED_CONTACT_LINK]:
        errors.append("notice must contain exactly one approved contact mail link")
    if visible.count(APPROVED_CONTACT) != 1 or html.count(APPROVED_CONTACT) != 2:
        errors.append("notice must contain exactly one visible approved contact address")

    allowed_external = {"https://amohelix.com/privacy", APPROVED_CONTACT_LINK}
    for link in parser.links:
        if link.startswith(("http://", "https://", "mailto:")):
            if link not in allowed_external:
                errors.append(f"unapproved external link: {link}")
            continue
        path = link.split("?", 1)[0].split("#", 1)[0]
        if not path or path in {"/", "/privacy"}:
            continue
        local = path.lstrip("/")
        if local not in inventory:
            errors.append(f"broken local link: {link}")

    if 'href="/privacy"' not in home:
        errors.append("homepage footer does not link to canonical privacy route")
    if "data-privacy-notice=" in home:
        errors.append("homepage must not masquerade as privacy notice")

    if "privacy.html" not in inventory or "privacy.css" not in inventory:
        errors.append("privacy notice must use root privacy.html and privacy.css files")
    if any(path.startswith("privacy/") for path in inventory):
        errors.append("consumed privacy directory-index layout is prohibited")

    exact_redirects = [
        "/privacy/ /privacy 301",
        "/privacy-policy /privacy 301",
        "/privacy-policy/ /privacy 301",
    ]
    actual_redirects = [line.strip() for line in redirects.splitlines() if line.strip()]
    if actual_redirects != exact_redirects:
        errors.append("route contract differs from the three approved permanent redirects")
    errors.extend(validate_privacy_routes(root, redirects, inventory))

    if config_text.count('name = "amo-helix-website"') != 1:
        errors.append("wrangler project must be exactly amo-helix-website")
    if "amo-helix-nexus-landing" in config_text:
        errors.append("wrangler project retains stale project identity")
    if "Authoritative Cloudflare Pages project: **amo-helix-website**." not in readme_text:
        errors.append("README does not bind the authoritative Pages project")
    if "amo-helix-nexus-landing" in readme_text:
        errors.append("README retains stale project identity")
    if "Cloudflare Pages project: `amo-helix-website`" not in doc_text:
        errors.append("deployment document does not bind the authoritative Pages project")
    if "amo-helix-nexus-landing" in doc_text:
        errors.append("deployment document retains stale project identity")

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
    print("PASS: privacy notice content, direct route, edge guard, links, scope, and project identity are source-ready")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
