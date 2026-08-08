#!/usr/bin/env python3
"""Crawl deduplicated PublicWWW competitor hits for public emails.

This performs public-page extraction only. It respects robots.txt, does not send
email, and labels deliverability as MX/DNS validation rather than mailbox proof.
"""

import csv
import html
import json
import re
import socket
import subprocess
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
from pathlib import Path
from threading import Lock
from urllib import robotparser
from urllib.parse import urljoin, urlparse, urldefrag

import requests

ROOT = Path(__file__).resolve().parent
INPUT = ROOT / "competitor_fingerprint_sites.csv"
RAW_SNIPPETS = ROOT / "competitor_fingerprint_raw.csv"
CHECKPOINT = ROOT / "competitor_public_email_scan.jsonl"
OUT_EMAILS = ROOT / "competitor_public_emails.csv"
OUT_SITES = ROOT / "competitor_public_email_sites.csv"
OUT_VALID = ROOT / "competitor_public_email_sites_valid_mx.csv"
OUT_EXCLUDED = ROOT / "competitor_public_email_excluded_advance_local.csv"
OUT_SUMMARY = ROOT / "competitor_public_email_summary.json"

MAX_WORKERS = 48
TIMEOUT = 10
UA = "CompetitorPublicEmailResearch/1.0 (+public contact page extraction; no email sent)"

EMAIL_RE = re.compile(r"(?i)\b[a-z0-9][a-z0-9._%+\-]*@[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+\b")
ROLE_RE = re.compile(r"(?i)(?:^|[._-])(info|contact|support|sales|hello|office|admin|service|help|media|press|editor|advertis|commercial|partner|partnership|team|webmaster|career|job|hr|recruit|legal|privacy|copyright|tip|social|marketing|web|enterprise|customer|customerservice)(?:$|[._-])")
PLACEHOLDER_RE = re.compile(r"(?i)^(?:name|user|you|example|email|test|admin)@(?:gmail\.com|your(?:company|brand|agency)\.com|domain\.com|example\.com|mail\.com|correo\.cl)$")
ASSET_TLDS = {"webp", "png", "jpg", "jpeg", "gif", "avif", "svg", "ico", "css", "js", "woff", "woff2", "ttf", "otf", "eot", "map", "pdf"}
PATH_KEYWORDS = ("contact", "about", "support", "help", "sales", "advertis", "team", "company", "office", "media", "press", "privacy", "legal", "terms", "copyright", "careers", "jobs")

ADVANCE_LOCAL = {
    "advance-ohio.com", "cleveland.com", "al.com", "alabamamediagroup.com", "masslive.com", "masslivemedia.com",
    "mlive.com", "mlivemediagroup.com", "oregonlive.com", "oregonianmediagroup.com", "silive.com",
    "statenislandmediagroup.com", "nj.com", "njadvancemedia.com", "pennlive.com", "thepamediagroup.com",
    "lehighvalleylive.com", "syracuse.com", "advancemediany.com", "newyorkupstate.com", "advancelocal.com",
    "advance.com", "advance.net", "siadvance.com",
}

PARENT_EMAIL_DOMAINS = {"advancelocal.com", "advance.com", "advance.net", "advance-ohio.com", "siadvance.com"}
THIRD_PARTY_DOMAINS = {
    "gmail.com", "googlemail.com", "outlook.com", "hotmail.com", "live.com", "yahoo.com", "yahoo.co.uk",
    "icloud.com", "me.com", "proton.me", "protonmail.com", "aol.com", "mail.com", "zoho.com",
    "zendesk.com", "hubspot.com", "mailchimp.com", "constantcontact.com", "sendgrid.net",
}
VENDOR_EXACT = {
    "hirevue.com", "vidcruiter.com", "sparkhire.com", "myinterview.com", "willo.video", "willotalent.com",
    "hackerrank.com", "codesignal.com", "codility.com", "testgorilla.com", "jobvite.com", "breezy.hr",
    "green-api.com", "twilio.com", "360dialog.com", "wati.io", "respond.io", "interakt.ai", "interakt.shop",
    "infobip.com", "gupshup.io", "vonage.com", "nexmo.com", "bird.com", "elevenlabs.io", "vapi.ai",
    "retellai.com", "bland.ai", "synthflow.ai", "voiceflow.com", "livekit.io", "poly.ai", "deepgram.com",
    "hume.ai", "play.ai", "ahrefs.com", "semrush.com", "seranking.com", "similarweb.com", "moz.com",
    "serpstat.com", "seobility.com", "conductor.com", "brightedge.com", "neilpatel.com", "ubersuggest.com",
}


def norm_domain(value):
    value = (value or "").strip().lower().rstrip(".")
    if "://" in value:
        value = urlparse(value).hostname or value
    value = value.split(":", 1)[0]
    if value.startswith("www."):
        value = value[4:]
    try:
        value = value.encode("idna").decode("ascii")
    except Exception:
        pass
    return value


def clean_email(value):
    value = html.unescape(value or "").strip().lower()
    value = value.replace("mailto:", "", 1).split("?", 1)[0]
    value = value.strip(" <>\"'()[]{}.,;:")
    if not EMAIL_RE.fullmatch(value):
        return None
    local, domain = value.rsplit("@", 1)
    if domain.rsplit(".", 1)[-1] in ASSET_TLDS or PLACEHOLDER_RE.fullmatch(value):
        return None
    if len(local) > 64 or len(value) > 254:
        return None
    return value


def same_seed(url, seed):
    host = norm_domain(urlparse(url).hostname or "")
    return bool(host and (host == seed or host.endswith("." + seed)))


def is_advance(domain):
    d = norm_domain(domain)
    return d in ADVANCE_LOCAL or any(d.endswith("." + root) for root in ADVANCE_LOCAL)


def is_vendor_domain(domain):
    d = norm_domain(domain)
    if d in VENDOR_EXACT:
        return True
    # Keep customer-specific hosted subdomains such as company.breezy.hr. Exclude
    # only obvious vendor infrastructure hosts.
    labels = d.split(".")
    if len(labels) >= 3 and labels[0] in {"www", "app", "api", "docs", "support", "dashboard", "status", "help"}:
        root = ".".join(labels[1:])
        if root in VENDOR_EXACT:
            return True
    return False


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.mailtos = []
        self.text = []
        self.title = []
        self.in_title = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag.lower() == "a":
            href = attrs.get("href")
            if href:
                self.links.append(href)
                if href.lower().startswith("mailto:"):
                    self.mailtos.append(href)
        if tag.lower() == "title":
            self.in_title = True

    def handle_endtag(self, tag):
        if tag.lower() == "title":
            self.in_title = False

    def handle_data(self, data):
        if data:
            self.text.append(data)
            if self.in_title:
                self.title.append(data)


def parse_page(content):
    parser = PageParser()
    try:
        parser.feed(content)
    except Exception:
        pass
    emails = set()
    for raw in parser.mailtos:
        e = clean_email(raw)
        if e:
            emails.add(e)
    visible = html.unescape(content) + "\n" + " ".join(parser.text)
    for raw in EMAIL_RE.findall(visible):
        e = clean_email(raw)
        if e:
            emails.add(e)
    return parser, emails


def fetch(session, url):
    try:
        response = session.get(url, timeout=TIMEOUT, allow_redirects=True, headers={"Accept": "text/html,application/xhtml+xml"})
        ctype = (response.headers.get("content-type") or "").lower()
        if response.status_code >= 400:
            return None, {"status": response.status_code, "url": response.url, "error": "http_error"}
        if "text/html" not in ctype and "application/xhtml+xml" not in ctype and not response.text.lstrip().startswith("<"):
            return None, {"status": response.status_code, "url": response.url, "error": "not_html"}
        if len(response.content) > 4_000_000:
            return None, {"status": response.status_code, "url": response.url, "error": "too_large"}
        return response.text, {"status": response.status_code, "url": response.url, "error": ""}
    except Exception as exc:
        return None, {"status": 0, "url": url, "error": type(exc).__name__}


def get_robots(session, seed, scheme):
    url = f"{scheme}://{seed}/robots.txt"
    try:
        response = session.get(url, timeout=TIMEOUT, headers={"User-Agent": UA, "Accept": "text/plain"})
        if response.status_code in (401, 403):
            return None, "blocked"
        if response.status_code != 200:
            return None, "unavailable"
        parser = robotparser.RobotFileParser()
        parser.set_url(url)
        parser.parse(response.text.splitlines())
        return parser, "ok"
    except Exception:
        return None, "unavailable"


def candidate_links(parser, base_url, seed):
    scored = []
    seen = set()
    for href in parser.links:
        if not href or href.lower().startswith(("mailto:", "javascript:", "#", "tel:")):
            continue
        url = urldefrag(urljoin(base_url, href))[0]
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not same_seed(url, seed):
            continue
        path = (parsed.path or "/").lower()
        score = sum(1 for keyword in PATH_KEYWORDS if keyword in path)
        if score <= 0 or url in seen:
            continue
        seen.add(url)
        scored.append((score, len(url), url))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [url for _, _, url in scored[:5]]


def extract_snippet_records():
    out = defaultdict(list)
    if not RAW_SNIPPETS.exists():
        return out
    with RAW_SNIPPETS.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            domain = norm_domain(row.get("domain", ""))
            if not domain or is_advance(domain) or is_vendor_domain(domain):
                continue
            for raw in EMAIL_RE.findall(html.unescape(row.get("snippet", ""))):
                email = clean_email(raw)
                if email:
                    out[domain].append({"email": email, "url": "", "source": "publicwww_snippet", "context": "unknown", "query": row.get("query", ""), "competitor": row.get("competitor", "")})
    return out


def load_input():
    rows = []
    with INPUT.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            domain = norm_domain(row.get("domain", ""))
            if not domain:
                continue
            row["domain"] = domain
            row["excluded_advance_local"] = "yes" if is_advance(domain) else ""
            row["vendor_domain"] = "yes" if is_vendor_domain(domain) else ""
            rows.append(row)
    return rows


def scan_one(row, snippet_records):
    seed = row["domain"]
    result = {
        "domain": seed,
        "excluded_advance_local": row.get("excluded_advance_local", ""),
        "vendor_domain": row.get("vendor_domain", ""),
        "competitors": row.get("competitors", ""),
        "categories": row.get("categories", ""),
        "queries": row.get("queries", ""),
        "confidences": row.get("confidences", ""),
        "publicwww_ranks": row.get("publicwww_ranks", ""),
        "homepage_url": "",
        "pages_checked": 0,
        "robots_status": "",
        "http_status": "",
        "emails": [],
        "evidence": [],
        "notes": [],
    }
    if result["excluded_advance_local"]:
        result["notes"].append("Advance Local excluded before crawling")
        return result
    if result["vendor_domain"]:
        result["notes"].append("competitor/vendor domain excluded from lead crawl")
        return result

    session = requests.Session()
    session.headers.update({"User-Agent": UA})
    robots_parser = None
    scheme = "https"
    for candidate_scheme in ("https", "http"):
        robots_parser, status = get_robots(session, seed, candidate_scheme)
        if status != "blocked":
            scheme = candidate_scheme
            result["robots_status"] = status
            break
        result["robots_status"] = status
    if result["robots_status"] == "blocked":
        result["notes"].append("robots.txt blocked")
        return result

    homepage = f"{scheme}://{seed}/"
    if robots_parser and not robots_parser.can_fetch(UA, homepage):
        result["notes"].append("homepage disallowed by robots.txt")
        return result
    content, meta = fetch(session, homepage)
    result["homepage_url"] = meta.get("url", homepage)
    result["http_status"] = meta.get("status", "")
    if not content:
        result["notes"].append(meta.get("error", "homepage_fetch_failed"))
        return result

    pages = [(result["homepage_url"], content)]
    parser, emails = parse_page(content)
    urls = candidate_links(parser, result["homepage_url"], seed)
    for url in urls:
        if robots_parser and not robots_parser.can_fetch(UA, url):
            continue
        page, page_meta = fetch(session, url)
        if page:
            pages.append((page_meta.get("url", url), page))
    all_records = []
    for url, page in pages:
        parser, page_emails = parse_page(page)
        context = "general"
        path = (urlparse(url).path or "/").lower()
        if any(k in path for k in ("privacy", "legal", "terms", "copyright", "dmca")):
            context = "legal"
        elif any(k in path for k in ("contact", "about", "support", "help", "sales", "team", "company", "office", "media", "press")):
            context = "contact"
        for email in page_emails:
            all_records.append({"email": email, "url": url, "source": "direct_page", "context": context, "competitor": ""})
    all_records.extend(snippet_records.get(seed, []))
    by_email = {}
    for record in all_records:
        old = by_email.get(record["email"])
        if old is None or (old["source"] == "publicwww_snippet" and record["source"] == "direct_page"):
            by_email[record["email"]] = record
    result["pages_checked"] = len(pages)
    result["emails"] = sorted(by_email)
    result["evidence"] = [by_email[email] for email in sorted(by_email)]
    if not result["emails"]:
        result["notes"].append("no public email found on homepage/contact pages or snippets")
    return result


def dns_status(domain):
    domain = norm_domain(domain)
    try:
        mx = subprocess.run(["dig", "+time=3", "+tries=1", "+short", "MX", domain], capture_output=True, text=True, timeout=6)
        if mx.returncode == 0 and mx.stdout.strip():
            return "valid_mx"
        a = subprocess.run(["dig", "+time=3", "+tries=1", "+short", "A", domain], capture_output=True, text=True, timeout=6)
        aaaa = subprocess.run(["dig", "+time=3", "+tries=1", "+short", "AAAA", domain], capture_output=True, text=True, timeout=6)
        if (a.stdout or "").strip() or (aaaa.stdout or "").strip():
            return "valid_a_fallback"
        return "no_mail_dns"
    except Exception:
        return "dns_error"


def classify_relationship(site, email_domain, counts):
    site = norm_domain(site)
    email_domain = norm_domain(email_domain)
    if email_domain == site or email_domain.endswith("." + site):
        return "site_domain"
    if email_domain in PARENT_EMAIL_DOMAINS or is_advance(site):
        return "parent_company"
    if email_domain in THIRD_PARTY_DOMAINS:
        return "third_party_provider"
    if counts.get(email_domain, 0) >= 2:
        return "shared_external_domain"
    return "external_company_domain"


def email_classification(email, context, relationship):
    local = email.split("@", 1)[0]
    if context == "legal" or re.search(r"(?i)(privacy|legal|copyright|dmca|terms|compliance|notice)", local):
        return "legal_or_privacy"
    if ROLE_RE.search(local):
        return "role_contact"
    if relationship == "third_party_provider":
        return "provider_contact"
    return "named_or_department_contact"


def main():
    rows = load_input()
    snippets = extract_snippet_records()
    # Resume safely from the JSONL checkpoint if a long crawl is interrupted.
    done = {}
    if CHECKPOINT.exists():
        with CHECKPOINT.open(encoding="utf-8") as handle:
            for line in handle:
                try:
                    item = json.loads(line)
                    done[item["domain"]] = item
                except Exception:
                    pass
    todo = [row for row in rows if row["domain"] not in done]
    print(f"input_sites={len(rows)} already_scanned={len(done)} todo={len(todo)} snippets_domains={len(snippets)}", flush=True)
    lock = Lock()
    with CHECKPOINT.open("a", encoding="utf-8") as handle:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = [executor.submit(scan_one, row, snippets) for row in todo]
            completed = 0
            for future in as_completed(futures):
                try:
                    item = future.result()
                except Exception as exc:
                    item = {"domain": "", "emails": [], "evidence": [], "notes": [f"worker_error:{type(exc).__name__}"]}
                if item.get("domain"):
                    done[item["domain"]] = item
                    handle.write(json.dumps(item, ensure_ascii=False) + "\n")
                    handle.flush()
                completed += 1
                if completed % 50 == 0 or completed == len(todo):
                    print(f"scanned={completed}/{len(todo)}", flush=True)

    ordered = [done.get(row["domain"], {"domain": row["domain"], "emails": [], "evidence": [], "notes": ["not_scanned"]}) for row in rows]
    # Only non-Advance/non-vendor websites become leads; preserve exclusions separately.
    included = [x for x in ordered if not x.get("excluded_advance_local") and not x.get("vendor_domain")]
    excluded = [x for x in ordered if x.get("excluded_advance_local")]
    all_email_records = []
    for item in included:
        by = {r["email"]: r for r in item.get("evidence", []) if clean_email(r.get("email", ""))}
        for email, evidence in by.items():
            all_email_records.append({"domain": item["domain"], "email": email, "context": evidence.get("context", "general"), "source": evidence.get("source", ""), "evidence_url": evidence.get("url", ""), "competitors": item.get("competitors", ""), "categories": item.get("categories", ""), "publicwww_ranks": item.get("publicwww_ranks", "")})
    counts = Counter(r["email"].rsplit("@", 1)[1] for r in all_email_records)
    unique_email_domains = sorted(counts)
    print(f"included_sites={len(included)} excluded_advance={len(excluded)} unique_emails={len(all_email_records)} unique_email_domains={len(unique_email_domains)}", flush=True)

    # DNS/MX validation is cached by email domain and never sends mail.
    dns = {}
    with ThreadPoolExecutor(max_workers=20) as executor:
        future_map = {executor.submit(dns_status, domain): domain for domain in unique_email_domains}
        for future in as_completed(future_map):
            domain = future_map[future]
            try:
                dns[domain] = future.result()
            except Exception:
                dns[domain] = "dns_error"
    print("dns_status_counts", dict(Counter(dns.values())), flush=True)

    email_rows = []
    for record in all_email_records:
        email = record["email"]
        email_domain = email.rsplit("@", 1)[1]
        relationship = classify_relationship(record["domain"], email_domain, counts)
        context = record["context"]
        email_rows.append({**record, "email_domain": email_domain, "domain_relationship": relationship, "email_classification": email_classification(email, context, relationship), "validation_status": dns.get(email_domain, "dns_error"), "validation_note": "MX/A DNS check only; no mailbox message sent", "email_domain_occurrences": counts[email_domain]})
    email_rows.sort(key=lambda x: (x["domain"], x["email"]))

    email_fields = ["domain", "email", "email_domain", "domain_relationship", "email_classification", "validation_status", "validation_note", "email_domain_occurrences", "context", "source", "evidence_url", "competitors", "categories", "publicwww_ranks"]
    with OUT_EMAILS.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=email_fields)
        writer.writeheader(); writer.writerows(email_rows)

    # One row per website, with multiple emails in the same relationship column.
    by_site = defaultdict(list)
    for record in email_rows:
        by_site[record["domain"]].append(record)
    site_fields = ["domain", "competitors", "categories", "publicwww_ranks", "homepage_url", "pages_checked", "robots_status", "http_status", "site_domain_valid_mx_emails", "parent_company_valid_mx_emails", "shared_external_valid_mx_emails", "external_company_valid_mx_emails", "all_valid_mx_emails", "email_count", "email_status", "notes"]
    site_rows = []
    for item in included:
        records = by_site.get(item["domain"], [])
        valid = [r for r in records if r["validation_status"] in {"valid_mx", "valid_a_fallback"}]
        def vals(rel):
            return sorted({r["email"] for r in valid if r["domain_relationship"] == rel})
        all_valid = sorted({r["email"] for r in valid})
        site_rows.append({
            "domain": item["domain"], "competitors": item.get("competitors", ""), "categories": item.get("categories", ""), "publicwww_ranks": item.get("publicwww_ranks", ""), "homepage_url": item.get("homepage_url", ""), "pages_checked": item.get("pages_checked", 0), "robots_status": item.get("robots_status", ""), "http_status": item.get("http_status", ""), "site_domain_valid_mx_emails": " ; ".join(vals("site_domain")), "parent_company_valid_mx_emails": " ; ".join(vals("parent_company")), "shared_external_valid_mx_emails": " ; ".join(vals("shared_external_domain")), "external_company_valid_mx_emails": " ; ".join(vals("external_company_domain")), "all_valid_mx_emails": " ; ".join(all_valid), "email_count": len(all_valid), "email_status": "valid_mx_email_found" if all_valid else ("public_email_no_mx" if records else "no_public_email_found"), "notes": " | ".join(item.get("notes", [])),
        })
    with OUT_SITES.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=site_fields); writer.writeheader(); writer.writerows(site_rows)
    with OUT_VALID.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=site_fields); writer.writeheader(); writer.writerows([r for r in site_rows if r["email_count"]])

    with OUT_EXCLUDED.open("w", newline="", encoding="utf-8") as handle:
        fields = ["domain", "excluded_advance_local", "competitors", "categories", "publicwww_ranks", "notes"]
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader()
        for item in excluded:
            writer.writerow({"domain": item["domain"], "excluded_advance_local": "yes", "competitors": item.get("competitors", ""), "categories": item.get("categories", ""), "publicwww_ranks": item.get("publicwww_ranks", ""), "notes": "Advance Local excluded before email verification"})

    summary = {
        "input_sites": len(rows), "vendor_domains_excluded": sum(bool(r.get("vendor_domain")) for r in rows), "advance_local_excluded": len(excluded), "included_sites": len(included), "public_email_records": len(email_rows), "valid_mx_or_a_fallback_records": sum(r["validation_status"] in {"valid_mx", "valid_a_fallback"} for r in email_rows), "validation_status_counts": dict(Counter(r["validation_status"] for r in email_rows)), "relationship_counts": dict(Counter(r["domain_relationship"] for r in email_rows)), "output_files": [OUT_EMAILS.name, OUT_SITES.name, OUT_VALID.name, OUT_EXCLUDED.name], "validation_limit": "MX/A DNS validation only; mailbox-level deliverability requires a separate verifier and was not claimed.",
    }
    OUT_SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
