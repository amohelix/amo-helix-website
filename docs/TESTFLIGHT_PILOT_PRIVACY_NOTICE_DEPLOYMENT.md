# TestFlight Pilot Privacy Notice Publication Plan

Status: source prepared; publication requires separate release approval

## Authority and route

- Repository: `amohelix/amo-helix-website`
- Cloudflare Pages project: `amo-helix-website`
- Canonical URL: `https://amohelix.com/privacy`
- Legacy route: `https://amohelix.com/privacy-policy` redirects to the canonical URL
- Source: standalone `privacy.html` in the website output directory
- Route contract: `_redirects` in the website output directory
- Pages behavior: standalone HTML files are served at extensionless paths, so
  `privacy.html` is the direct `200` source for `/privacy`
- Edge transformation guard: the approved contact link is wrapped in the
  documented `email_off` comments so zone-level obfuscation does not inject a
  decoder script into this notice

Cloudflare references:

- [Serving Pages](https://developers.cloudflare.com/pages/configuration/serving-pages/)
- [Email Address Obfuscation](https://developers.cloudflare.com/waf/tools/scrape-shield/email-address-obfuscation/)

The parent website commit is byte-identical to the live homepage at the source
checkpoint. This change does not alter Cloudflare, DNS, Pages settings, runtime
configuration, cookies, analytics, forms, or application behavior.

## Scope boundary

The notice is publication-ready only for the private U.S. TestFlight
synthetic-staging pilot. It is not a broader customer-pilot or production
privacy policy and does not authorize real customer data. Broader legal and
privacy review remains required before operational customer or real-data use.

The notice preserves the locked one-platform internationalization direction.
It introduces no locale schema, translation, Brazil or LGPD implementation,
regional infrastructure, or country-specific product fork.

## Proposed publication sequence

1. Release control approves the exact source commit, content hash, render, and
   test evidence.
2. Confirm the deployment source is still the same Cloudflare Pages project
   and the live homepage still matches the sealed parent identity.
3. Deploy the accepted commit once through the existing Pages workflow without
   changing DNS, bindings, functions, or environment variables.
4. Verify `/privacy` returns HTTP 200 directly, `/privacy/` and both
   `/privacy-policy` variants permanently redirect to `/privacy`, the notice
   retains the exact canonical title and approved content, the homepage footer
   link works, and no other route changed.
5. Record the deployment and post-deploy route evidence before entering the
   URL in App Store Connect under a separately authorized D1-E window.

## Stop conditions

Stop before publication on source drift, different Pages ownership, route
collision, content change, unsupported privacy claim, broken link, homepage
fallback, unexpected tracking, DNS requirement, or any need to alter runtime
bindings or the pilot-request functions.
