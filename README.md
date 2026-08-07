# PublicWWW Typeform — verified one-row-per-domain CSV

Canonical team-facing file: `top1000_typeform_one_domain_verified.csv`

- Exactly 1,000 rows and 1,000 unique domains.
- The `emails` column contains directly verified same-domain emails, separated by ` ; `.
- `email_verification` reports each address as `valid`, `invalid`, `risky`, or `unknown`, with the verifier reason.
- `valid_emails`, `invalid_emails`, `risky_emails`, and `unknown_emails` provide filtered lists.
- `verification_summary` counts each verdict per domain.

## Verification results

- 1,502 unique email addresses checked.
- 1,376 `deliverable` / valid.
- 120 `undeliverable` / invalid.
- 1 `risky`.
- 5 `unknown`.

The provider's `deliverable` verdict is the valid bucket; `undeliverable` is the invalid bucket. `risky` and `unknown` should not be treated as confirmed valid or invalid without further review. A verifier/MX result also does not guarantee that the mailbox owner wants unsolicited contact.

The API key was used transiently and is not included in the repository or CSV files. Rotate the key after this run because it was shared in chat.
