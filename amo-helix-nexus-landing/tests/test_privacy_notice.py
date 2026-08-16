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
        cls.notice = (ROOT / "privacy.html").read_text(encoding="utf-8")
        cls.home = (ROOT / "index.html").read_text(encoding="utf-8")
        cls.redirects = (ROOT / "_redirects").read_text(encoding="utf-8")
        cls.paths = VALIDATOR.file_inventory(ROOT)
        cls.project_config = (ROOT / "wrangler.toml").read_text(encoding="utf-8")
        cls.readme = (ROOT / "README.md").read_text(encoding="utf-8")
        cls.deployment_doc = VALIDATOR.DEPLOYMENT_DOC.read_text(encoding="utf-8")

    def validate(
        self,
        notice: str | None = None,
        home: str | None = None,
        redirects: str | None = None,
        paths: set[str] | None = None,
        project_config: str | None = None,
        readme: str | None = None,
        deployment_doc: str | None = None,
    ) -> list[str]:
        return VALIDATOR.validate_notice(
            notice if notice is not None else self.notice,
            home if home is not None else self.home,
            redirects if redirects is not None else self.redirects,
            ROOT,
            paths=paths if paths is not None else self.paths,
            project_config=project_config if project_config is not None else self.project_config,
            readme=readme if readme is not None else self.readme,
            deployment_doc=deployment_doc if deployment_doc is not None else self.deployment_doc,
        )

    def test_exact_notice_passes(self) -> None:
        self.assertEqual([], self.validate())

    def test_marketing_homepage_fallback_fails(self) -> None:
        self.assertTrue(self.validate(notice=self.home))

    def test_missing_scope_marker_fails(self) -> None:
        changed = self.notice.replace(' data-privacy-notice="testflight-synthetic-staging"', "")
        self.assertIn("missing exact synthetic-staging document marker", self.validate(notice=changed))

    def test_placeholder_or_draft_label_fails(self) -> None:
        tokens = (("PLACEHOLDER", "forbidden placeholder"), ("DRAFT", "forbidden draft label"), ("TBD", "forbidden draft label"))
        for token, expected in tokens:
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

    def test_script_form_or_tracker_fails(self) -> None:
        script = self.notice.replace("</body>", '<script src="/analytics.js"></script></body>')
        self.assertIn("notice must not contain scripts or forms", self.validate(notice=script))
        self.assertIn("tracking or analytics token found", self.validate(notice=script))
        form = self.notice.replace("</body>", "<form></form></body>")
        self.assertIn("notice must not contain scripts or forms", self.validate(notice=form))

    def test_broken_link_fails(self) -> None:
        changed = self.notice.replace('href="/"', 'href="/missing-page"', 1)
        self.assertIn("broken local link: /missing-page", self.validate(notice=changed))

    def test_email_guard_and_exact_contact_pass(self) -> None:
        self.assertEqual(1, self.notice.count(VALIDATOR.GUARDED_CONTACT))
        self.assertEqual([], self.validate())

    def test_missing_incomplete_or_duplicate_email_guard_fails(self) -> None:
        missing = self.notice.replace("<!--email_off-->", "").replace("<!--/email_off-->", "")
        self.assertIn("contact must have exactly one complete email_off guard", self.validate(notice=missing))
        incomplete = self.notice.replace("<!--/email_off-->", "")
        self.assertIn("contact must have exactly one complete email_off guard", self.validate(notice=incomplete))
        duplicate = self.notice.replace(VALIDATOR.GUARDED_CONTACT, VALIDATOR.GUARDED_CONTACT * 2)
        errors = self.validate(notice=duplicate)
        self.assertIn("contact must have exactly one complete email_off guard", errors)
        self.assertIn("notice must contain exactly one approved contact mail link", errors)

    def test_mismatched_or_extra_contact_fails(self) -> None:
        mismatched = self.notice.replace("mailto:Kevin@amohelix.com", "mailto:other@amohelix.com")
        self.assertIn("approved contact link must be exactly enclosed by email_off guard", self.validate(notice=mismatched))
        extra = self.notice.replace("</body>", '<a href="mailto:other@amohelix.com">Other</a></body>')
        self.assertIn("notice must contain exactly one approved contact mail link", self.validate(notice=extra))

    def test_consumed_directory_index_layout_fails(self) -> None:
        consumed = set(self.paths)
        consumed.remove("privacy.html")
        consumed.remove("privacy.css")
        consumed.update({"privacy/index.html", "privacy/privacy.css"})
        errors = self.validate(paths=consumed)
        self.assertIn("privacy notice must use root privacy.html and privacy.css files", errors)
        self.assertIn("consumed privacy directory-index layout is prohibited", errors)

    def test_direct_file_route_contract(self) -> None:
        self.assertEqual([], VALIDATOR.validate_privacy_routes(ROOT, self.redirects, self.paths))

    def test_consumed_rewrite_and_redirect_drift_fail(self) -> None:
        consumed = self.redirects.replace("/privacy/ /privacy 301", "/privacy /privacy/index.html 200")
        self.assertIn(
            "route contract differs from the three approved permanent redirects",
            self.validate(redirects=consumed),
        )
        missing = self.redirects.replace("/privacy-policy/ /privacy 301\n", "")
        self.assertIn(
            "route contract differs from the three approved permanent redirects",
            self.validate(redirects=missing),
        )

    def test_homepage_must_link_to_notice(self) -> None:
        changed = self.home.replace('<a href="/privacy">Privacy</a>', "")
        self.assertIn("homepage footer does not link to canonical privacy route", self.validate(home=changed))

    def test_project_identity_is_fail_closed(self) -> None:
        stale_config = self.project_config.replace("amo-helix-website", "amo-helix-nexus-landing")
        self.assertIn("wrangler project must be exactly amo-helix-website", self.validate(project_config=stale_config))
        stale_doc = self.deployment_doc.replace(
            "Cloudflare Pages project: `amo-helix-website`",
            "Cloudflare Pages project: `amo-helix-nexus-landing`",
        )
        self.assertIn("deployment document does not bind the authoritative Pages project", self.validate(deployment_doc=stale_doc))


if __name__ == "__main__":
    unittest.main()
