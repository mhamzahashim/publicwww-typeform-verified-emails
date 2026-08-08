# Competitor PublicWWW lead exports

Run date: 2026-08-08 UTC

## What was done

- Ran 46 verified PublicWWW fingerprint queries.
- Collected 2,795 unique PublicWWW result domains and deduplicated them by domain.
- Crawled public homepages and up to five same-domain contact/about/support pages, respecting robots.txt.
- Extracted 4,702 public email candidates.
- Excluded vendor infrastructure domains from lead outputs.
- Excluded the configured Advance Local domain list before email validation. No Advance Local domain appeared in the result set.
- Validated email domains using DNS MX records, with A/AAAA fallback noted separately.
- Classified relationships as `site_domain`, `parent_company`, `shared_external_domain`, `external_company_domain`, or `third_party_provider`.

## Important validation limitation

No mailbox-verification API key was available. `valid_mx` means the email domain publishes an MX record; `valid_a_fallback` means it has an A/AAAA record and may accept mail under fallback rules. Neither proves that the individual mailbox exists. No email was sent.

## Recommended files

- `competitor_only_public_email_sites_valid_role_mx.csv` — best outreach subset: one row per website, strict MX only, role/contact addresses, multiple emails combined in one cell.
- `competitor_only_public_email_sites_valid_mx_strict.csv` — one row per website, strict MX only, all relationship classes.
- `competitor_only_public_email_sites_valid_dns.csv` — one row per website, MX plus A/AAAA fallback.
- `competitor_only_public_emails_valid_mx.csv` — one row per strict-MX email.
- `competitor_public_emails.csv` — all extracted emails with relationship/classification and validation status.
- `competitor_only_excluded_advance_local.csv` — complete Advance Local exclusion audit.
- `competitor_lead_export_summary.json` — counts and validation notes.

## Summary

- 697 competitor-matched websites have at least one MX/A-valid public email.
- 623 have at least one strict-MX-valid public email.
- 335 have at least one strict-MX-valid role/contact email.
- 1,858 strict-MX email records are in the competitor-only export.

The PublicWWW API key was read interactively and was not written to disk. Because it was pasted into chat, rotate/revoke it after this run.
