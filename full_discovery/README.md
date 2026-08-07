# Full PublicWWW Typeform discovery

Generated from the PublicWWW API on 2026-08-07.

## Files

Start with [`VIEW_ME_FIRST.md`](VIEW_ME_FIRST.md), or download the formatted [Excel workbook](typeform_leads_readable.xlsx).

- `valid_emails_display.csv` — small, readable one-row-per-email list of the verified subset.
- `valid_domains_display.csv` — one-row-per-domain list of domains with verified emails.
- `email_candidates_display.csv` — readable candidate list from the PublicWWW email query.
- `all_domains_part_01.csv` through `all_domains_part_08.csv` — complete domain list split into browser-friendly files.

- `typeform_all_one_domain_verified.csv` — canonical one-row-per-domain output with PublicWWW email candidates, indexed Typeform URL columns, and verification columns.
- `typeform_all_one_domain_with_indexed_forms.csv` — discovery output before vrfymail results.
- `typeform_verified_site_contact_emails.csv` — only domains with at least one `deliverable` same-domain role mailbox.
- `typeform_sites_with_publicwww_emails.csv` — domains returned by the same-page email query.
- `typeform_sites_without_publicwww_emails.csv` — domains with no candidate from that query.
- `typeform_excluded_corporate_brands.csv` — Advance Local domains excluded from verification.
- `typeform_email_verification_queue.csv` — audit queue showing classifications and the exact addresses eligible for verification.
- `typeform_indexed_form_url_evidence.csv` — audit rows for exact Typeform URLs extracted from PublicWWW snippets.

## Important interpretation

The complete `depth:all embed.typeform.com` export contained 35,786 source rows. The team-facing files collapse three `www.` aliases into canonical domains, so they contain 35,783 unique domains with no duplicate domain rows.

`typeform_indexed_match=yes` means PublicWWW's separate `depth:all "typeform.com/to/"` query matched the domain. `typeform_form_urls` contains exact URLs only when the PublicWWW snippet export exposed the URL; snippet downloads are plan-limited, so a blank URL cell does **not** mean that the domain has no form. The full-match flag is the broader indexed evidence.

Emails were classified conservatively. Only same-domain role mailboxes were placed in the verification queue; Advance Local domains were hard-excluded. `valid_emails` means vrfymail returned `deliverable`; risky, unknown, and undeliverable results remain in their separate columns.

Use applicable privacy, anti-spam, and website terms when contacting organizations.
