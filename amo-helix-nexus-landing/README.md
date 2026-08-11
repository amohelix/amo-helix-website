# AMO Helix — Nexus Landing Page

A responsive, dependency-free landing page for **Nexus by AMO Helix**.

## What is included

- Branded responsive homepage
- 15-second AMO Helix intro film
- Voice AI product demonstration
- Configurable industry examples
- Human-review and governance positioning
- Pilot inquiry form with a Cloudflare Pages Function endpoint
- Mobile navigation
- Accessibility basics and reduced-motion support
- Favicons and brand imagery

## Preview locally

Open `index.html` directly, or run a local server:

```bash
python3 -m http.server 8080
```

Then open `http://localhost:8080`.

## Deploy to Cloudflare Pages

1. Upload this folder to a Git repository, or use Cloudflare Pages direct upload.
2. Framework preset: **None**.
3. Build command: leave blank.
4. Output directory: `/`.
5. Connect your domain after deployment.

## Pilot request delivery

The pilot form posts to `/api/pilot-request`, implemented in `functions/api/pilot-request.js`.

Configure at least one delivery path in Cloudflare Pages.

### Cloudflare D1 storage

- Create a D1 database for pilot requests.
- Add it to the Pages project as a D1 binding named `PILOT_REQUESTS_DB`.
- The function creates the `pilot_requests` table automatically on first successful submission.

### Webhook delivery

- `PILOT_REQUEST_WEBHOOK_URL`: HTTPS endpoint for Zapier, Make, Slack workflow, CRM, or an internal lead receiver.
- `PILOT_REQUEST_WEBHOOK_SECRET`: optional bearer token sent in the `Authorization` header.

### Email delivery with Resend

- `RESEND_API_KEY`: Resend API key.
- `PILOT_REQUEST_TO`: inbox that receives pilot requests.
- `PILOT_REQUEST_FROM`: verified sender, for example `AMO Helix <pilot@amohelix.com>`.

## Before public launch

- Add final legal pages: Privacy, Terms, Cookie Notice, and Accessibility.
- Confirm trademark and domain clearance.
- Replace any product statements that are not yet implemented with verified launch capabilities.
- Add analytics only after selecting a privacy approach.


## v4 — Locked approved AMO Helix brand assets

This release removes all improvised or regenerated logo substitutes.

Authoritative assets:
- `assets/amo-helix-approved-icon-v4-*.png`: exact crop of the approved dark AMO app icon from the user-supplied brand board.
- `assets/amo-helix-approved-long-logo-v4.png`: transparent derivative of the exact user-approved long AMO + mechanical helix + HELIX artwork.
- `assets/APPROVED-BRAND-BOARD-SOURCE.jpg`: untouched approved brand-board source.
- `assets/APPROVED-LONG-LOGO-SOURCE.jpg`: untouched approved long-logo source.

Do not replace these assets without explicit approval.
