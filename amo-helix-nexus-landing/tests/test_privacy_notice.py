from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "privacy_validator", ROOT / "scripts" / "validate_privacy_notice.py"
)
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


class PrivacyNoticeContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.notice = (ROOT / "privacy" / "index.html").read_text(encoding="utf-8")
        cls.home = (ROOT / "index.html").read_text(encoding="utf-8")
        cls.redirects = (ROOT / "_redirects").read_text(encoding="utf-8")

    def validate(self, notice: str | None = None, home: str | None = None, redirects: str | None = None):
        return VALIDATOR.validate_notice(
            notice if notice is not None else self.notice,
            home if home is not None else self.home,
            redirects if redirects is not None else self.redirects,
            ROOT,
        )

    def test_exact_notice_passes(self) -> None:
        self.assertEqual([], self.validate())

    def test_marketing_homepage_fallback_fails(self) -> None:
        self.assertTrue(self.validate(notice=self.home))

    def test_missing_scope_marker_fails(self) -> None:
        changed = self.notice.replace(' data-privacy-notice="testflight-synthetic-staging"', "")
        self.assertIn("missing exact synthetic-staging document marker", self.validate(notice=changed))

    def test_placeholder_or_draft_label_fails(self) -> None:
        for token, expected in (("PLACEHOLDER", "forbidden placeholder"), ("DRAFT", "forbidden draft label"), ("TBD", "forbidden draft label")):
            with self.subTest(token=token):
                changed = self.notice.replace("Questions or requests", f"{token} Questions or requests")
                self.assertIn(expected, self.validate(notice=changed))

    def test_unsupported_claims_fail(self) -> None:
        claims = (
            "AMO Helix is GDPR compliant.",
            "AMO Helix is SOC 2 certified.",
            "We never share information with service providers.",
            "We delete all records after 30 days.",
        )
        for claim in claims:
            with self.subTest(claim=claim):
                changed = self.notice.replace("Questions or requests", f"{claim} Questions or requests")
                self.assertTrue(self.validate(notice=changed))

    def test_tracking_script_fails(self) -> None:
        changed = self.notice.replace("</body>", '<script src="/analytics.js"></script></body>')
        errors = self.validate(notice=changed)
        self.assertIn("notice must not contain scripts or forms", errors)
        self.assertIn("tracking or analytics token found", errors)

    def test_broken_link_fails(self) -> None:
        changed = self.notice.replace('href="/"', 'href="/missing-page"', 1)
        self.assertIn("broken local link: /missing-page", self.validate(notice=changed))

    def test_legacy_route_must_redirect_to_canonical(self) -> None:
        changed = self.redirects.replace("/privacy-policy /privacy 301", "/privacy-policy /index.html 200")
        self.assertIn(
            "route contract differs from the four approved privacy mappings",
            self.validate(redirects=changed),
        )

    def test_homepage_must_link_to_notice(self) -> None:
        changed = self.home.replace('<a href="/privacy">Privacy</a>', "")
        self.assertIn("homepage footer does not link to canonical privacy route", self.validate(home=changed))


if __name__ == "__main__":
    unittest.main()
