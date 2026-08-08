#!/usr/bin/env python3
"""Build strict MX and competitor-only lead exports from the crawl results."""

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EMAIL_INPUT = ROOT / "competitor_public_emails.csv"
SITE_INPUT = ROOT / "competitor_public_email_sites.csv"
OUT_EMAIL_ALL = ROOT / "competitor_only_public_emails_valid_mx.csv"
OUT_SITE_DNS = ROOT / "competitor_only_public_email_sites_valid_dns.csv"
OUT_SITE_MX = ROOT / "competitor_only_public_email_sites_valid_mx_strict.csv"
OUT_SITE_ROLE = ROOT / "competitor_only_public_email_sites_valid_role_mx.csv"
OUT_EXCLUDED = ROOT / "competitor_only_excluded_advance_local.csv"
OUT_STATS = ROOT / "competitor_lead_export_summary.json"

ADVANCE = {"advance-ohio.com", "cleveland.com", "al.com", "alabamamediagroup.com", "masslive.com", "masslivemedia.com", "mlive.com", "mlivemediagroup.com", "oregonlive.com", "oregonianmediagroup.com", "silive.com", "statenislandmediagroup.com", "nj.com", "njadvancemedia.com", "pennlive.com", "thepamediagroup.com", "lehighvalleylive.com", "syracuse.com", "advancemediany.com", "newyorkupstate.com", "advancelocal.com", "advance.com", "advance.net", "siadvance.com"}


def is_advance(domain):
    d = (domain or "").lower().strip().rstrip(".")
    return d in ADVANCE or any(d.endswith("." + root) for root in ADVANCE)


def vals(value):
    return [x.strip() for x in (value or "").split(" ; ") if x.strip()]


def is_competitor_row(row):
    cats = set(vals(row.get("categories")))
    return bool(cats - {"target"})


def grouped_site_rows(email_rows, site_meta):
    by_site = defaultdict(list)
    for row in email_rows:
        by_site[row["domain"]].append(row)
    fields = ["domain", "competitors", "categories", "publicwww_ranks", "homepage_url", "pages_checked", "robots_status", "http_status", "site_domain_emails", "parent_company_emails", "shared_external_emails", "external_company_emails", "third_party_provider_emails", "all_emails", "email_count", "email_status", "notes"]
    output = []
    for domain, meta in site_meta.items():
        records = by_site.get(domain, [])
        def emails_for(predicate):
            return sorted({r["email"] for r in records if predicate(r)})
        all_emails = sorted({r["email"] for r in records})
        def rel(name):
            return lambda r: r["domain_relationship"] == name
        row = {
            "domain": domain,
            "competitors": meta.get("competitors", ""),
            "categories": meta.get("categories", ""),
            "publicwww_ranks": meta.get("publicwww_ranks", ""),
            "homepage_url": meta.get("homepage_url", ""),
            "pages_checked": meta.get("pages_checked", ""),
            "robots_status": meta.get("robots_status", ""),
            "http_status": meta.get("http_status", ""),
            "site_domain_emails": " ; ".join(emails_for(rel("site_domain"))),
            "parent_company_emails": " ; ".join(emails_for(rel("parent_company"))),
            "shared_external_emails": " ; ".join(emails_for(rel("shared_external_domain"))),
            "external_company_emails": " ; ".join(emails_for(rel("external_company_domain"))),
            "third_party_provider_emails": " ; ".join(emails_for(rel("third_party_provider"))),
            "all_emails": " ; ".join(all_emails),
            "email_count": len(all_emails),
            "email_status": "valid_mx_email_found" if all_emails else "no_strict_mx_email_found",
            "notes": meta.get("notes", ""),
        }
        output.append(row)
    return fields, output


def write_csv(path, fields, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)


def main():
    emails = list(csv.DictReader(EMAIL_INPUT.open(encoding="utf-8", newline="")))
    sites = list(csv.DictReader(SITE_INPUT.open(encoding="utf-8", newline="")))
    site_meta = {r["domain"]: r for r in sites if not is_advance(r["domain"]) and is_competitor_row(r)}
    email_competitors = [r for r in emails if r["domain"] in site_meta and r["validation_status"] == "valid_mx"]
    email_fields = ["domain", "email", "email_domain", "domain_relationship", "email_classification", "validation_status", "validation_note", "email_domain_occurrences", "context", "source", "evidence_url", "competitors", "categories", "publicwww_ranks"]
    write_csv(OUT_EMAIL_ALL, email_fields, email_competitors)

    # DNS-level export includes MX and A-fallback; strict export includes MX only.
    strict_by_site = defaultdict(list)
    dns_by_site = defaultdict(list)
    for row in emails:
        if row["domain"] not in site_meta:
            continue
        if row["validation_status"] in {"valid_mx", "valid_a_fallback"}:
            dns_by_site[row["domain"]].append(row)
        if row["validation_status"] == "valid_mx":
            strict_by_site[row["domain"]].append(row)
    _, dns_rows = grouped_site_rows([item for records in dns_by_site.values() for item in records], site_meta)
    _, mx_rows = grouped_site_rows([item for records in strict_by_site.values() for item in records], site_meta)
    role_by_site = defaultdict(list)
    for domain, records in strict_by_site.items():
        role_by_site[domain] = [r for r in records if r["email_classification"] == "role_contact"]
    _, role_rows = grouped_site_rows([item for records in role_by_site.values() for item in records], site_meta)
    site_fields = ["domain", "competitors", "categories", "publicwww_ranks", "homepage_url", "pages_checked", "robots_status", "http_status", "site_domain_emails", "parent_company_emails", "shared_external_emails", "external_company_emails", "third_party_provider_emails", "all_emails", "email_count", "email_status", "notes"]
    write_csv(OUT_SITE_DNS, site_fields, [r for r in dns_rows if r["email_count"]])
    write_csv(OUT_SITE_MX, site_fields, [r for r in mx_rows if r["email_count"]])
    write_csv(OUT_SITE_ROLE, site_fields, [r for r in role_rows if r["email_count"]])
    matched_advance = {r["domain"]: r for r in sites if is_advance(r["domain"])}
    with OUT_EXCLUDED.open("w", newline="", encoding="utf-8") as handle:
        fields = ["domain", "excluded_advance_local", "present_in_fingerprint_results", "competitors", "categories", "publicwww_ranks", "notes"]
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader()
        for domain in sorted(ADVANCE):
            item = matched_advance.get(domain, {})
            writer.writerow({"domain": domain, "excluded_advance_local": "yes", "present_in_fingerprint_results": "yes" if item else "no", "competitors": item.get("competitors", ""), "categories": item.get("categories", ""), "publicwww_ranks": item.get("publicwww_ranks", ""), "notes": "Advance Local excluded before email verification"})

    stats = {
        "competitor_sites_with_any_strict_mx_email": len([r for r in mx_rows if r["email_count"]]),
        "competitor_sites_with_any_dns_email": len([r for r in dns_rows if r["email_count"]]),
        "competitor_sites_with_role_strict_mx_email": len([r for r in role_rows if r["email_count"]]),
        "strict_mx_email_rows": len(email_competitors),
        "relationship_counts_strict_mx": dict(Counter(r["domain_relationship"] for r in email_competitors)),
        "excluded_advance_local": len([r for r in sites if is_advance(r["domain"])]),
        "files": [OUT_EMAIL_ALL.name, OUT_SITE_DNS.name, OUT_SITE_MX.name, OUT_SITE_ROLE.name, OUT_EXCLUDED.name],
        "validation_note": "Strict export requires an MX record. This is domain-level validation, not mailbox-level deliverability.",
    }
    OUT_STATS.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
