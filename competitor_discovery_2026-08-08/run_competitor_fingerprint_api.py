#!/usr/bin/env python3
"""Run the verified PublicWWW competitor fingerprints without persisting the API key."""

import csv
import getpass
import io
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW_DIR = ROOT / "fingerprint_raw"
RAW_DIR.mkdir(exist_ok=True)
RAW_OUT = ROOT / "competitor_fingerprint_raw.csv"
DEDUP_OUT = ROOT / "competitor_fingerprint_sites.csv"
STATUS_OUT = ROOT / "competitor_fingerprint_query_status.json"
UA = "PublicWWWFingerprintResearch/1.0"

# The exact strings are copied from the verified query pack. Weak queries are retained
# for completeness but confidence is preserved so they are not mistaken for proof.
QUERIES = [
    ("target", "HireVue", 'depth:all "app.hirevue.com"', "medium"),
    ("target", "HireVue invitation", 'depth:all "go.hirevue.com/interviews/"', "medium"),
    ("target", "Green API", 'depth:all "/waInstance" "/sendMessage/"', "low"),
    ("target", "Green API host", 'depth:all "api.green-api.com" "sendMessage"', "low"),
    ("target", "ElevenLabs Agents", 'depth:all "unpkg.com/@elevenlabs/convai-widget-embed"', "high"),
    ("target", "ElevenLabs element", 'depth:all "elevenlabs-convai"', "high"),
    ("target", "Ahrefs", 'depth:0 "ahrefs-site-verification"', "high"),

    ("hirevue", "VidCruiter", 'depth:all "vidcruiter.com"', "weak"),
    ("hirevue", "Spark Hire", 'depth:all "sparkhire.com/interview/"', "medium"),
    ("hirevue", "myInterview", 'depth:all "embed.myinterview.com/widget/"', "high"),
    ("hirevue", "Willo", 'depth:all "app.willotalent.com"', "medium"),
    ("hirevue", "HackerRank", 'depth:all "hackerrank.com/tests/"', "medium"),
    ("hirevue", "CodeSignal", 'depth:all "codesignal.com"', "weak"),
    ("hirevue", "Codility", 'depth:all "app.codility.com/test/"', "medium-high"),
    ("hirevue", "TestGorilla", 'depth:all "assessment.testgorilla.com/testtaker/"', "high"),
    ("hirevue", "Jobvite", 'depth:all "jobs.jobvite.com"', "high"),
    ("hirevue", "Breezy HR", 'depth:all "breezy.hr/p/"', "medium"),

    ("whatsapp", "Meta WhatsApp Cloud API", 'depth:all "graph.facebook.com" "messaging_product" "whatsapp"', "low-medium"),
    ("whatsapp", "Twilio", 'depth:all "api.twilio.com/2010-04-01/Accounts" "whatsapp:"', "low-medium"),
    ("whatsapp", "360dialog", 'depth:all "waba.360dialog.io/v1/messages"', "medium"),
    ("whatsapp", "WATI", 'depth:all "/api/ext/v3/"', "low-medium"),
    ("whatsapp", "respond.io", 'depth:all "api.respond.io/v2"', "low-medium"),
    ("whatsapp", "Interakt", 'depth:all "api.interakt.ai/v1/public/message/"', "low-medium"),
    ("whatsapp", "Infobip", 'depth:all "api.infobip.com/whatsapp/1/"', "low-medium"),
    ("whatsapp", "Gupshup", 'depth:all "api.gupshup.io/wa/api/v1/"', "low-medium"),
    ("whatsapp", "Vonage", 'depth:all "api.nexmo.com/v1/messages" "channel" "whatsapp"', "low-medium"),
    ("whatsapp", "Bird / MessageBird", 'depth:all "platform.bird.com/v1/whatsapp/messages"', "low-medium"),

    ("voice", "Vapi", 'depth:all "unpkg.com/@vapi-ai/client-sdk-react/dist/embed/widget.umd.js"', "high"),
    ("voice", "Retell AI", 'depth:all "dashboard.retellai.com/retell-widget-v2.js"', "high"),
    ("voice", "Bland AI", 'depth:all "widget.bland.ai/loader.js"', "high"),
    ("voice", "Synthflow", 'depth:all "api.synthflow.ai/v2/chat/"', "low"),
    ("voice", "Voiceflow", 'depth:all "cdn.voiceflow.com/widget-next/bundle.mjs"', "high"),
    ("voice", "LiveKit", 'depth:all "cloud.livekit.io/embed-popup.js"', "high"),
    ("voice", "PolyAI", 'depth:all "platform.polyai.app"', "low"),
    ("voice", "Deepgram Voice Agent", 'depth:all "@deepgram/agents-widget"', "low"),
    ("voice", "Hume EVI", 'depth:all "api.hume.ai/v0/evi/chat"', "low"),

    ("seo", "Ahrefs", 'depth:0 "ahrefs-site-verification"', "high"),
    ("seo", "Semrush", 'depth:all "semrush"', "weak"),
    ("seo", "SE Ranking", 'depth:all "SEBot-WA"', "weak"),
    ("seo", "Similarweb", 'depth:all "similarweb"', "weak"),
    ("seo", "Moz Pro", 'depth:all "moz.com"', "weak"),
    ("seo", "Serpstat", 'depth:all "serpstat"', "weak"),
    ("seo", "Seobility", 'depth:all "seobility"', "weak"),
    ("seo", "Conductor", 'depth:all "conductor.com"', "weak"),
    ("seo", "BrightEdge", 'depth:all "brightedge"', "weak"),
    ("seo", "Ubersuggest", 'depth:all "ubersuggest"', "weak"),
]


def slug(value):
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")[:80]


def request_query(key, query):
    encoded = urllib.parse.quote(query, safe="")
    url = f"https://publicwww.com/websites/{encoded}/?key={urllib.parse.quote(key, safe='')}&export=csvsnippets"
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/csv,*/*"})
    with urllib.request.urlopen(req, timeout=90) as response:
        return response.status, response.headers.get("content-type", ""), response.read()


def parse_rows(body):
    text = body.decode("utf-8", "replace")
    records = []
    for line in text.splitlines():
        if not line.strip():
            continue
        parts = line.split(";", 2)
        if len(parts) < 2:
            continue
        domain = parts[0].strip().lower()
        rank = parts[1].strip()
        if not domain or domain.lower() in {"site", "error", "message"}:
            continue
        records.append((domain, rank, parts[2].strip() if len(parts) == 3 else ""))
    return records


def main():
    key = getpass.getpass("PublicWWW API key: ").strip()
    if not key:
        raise SystemExit("API key was empty")

    statuses = []
    all_rows = []
    for index, (category, competitor, query, confidence) in enumerate(QUERIES, 1):
        filename = RAW_DIR / f"{index:02d}_{slug(category)}_{slug(competitor)}.csvsnippets"
        record = {"index": index, "category": category, "competitor": competitor, "query": query, "confidence": confidence, "status": 0, "bytes": 0, "rows": 0, "domains": 0, "error": ""}
        try:
            status, content_type, body = request_query(key, query)
            filename.write_bytes(body)
            parsed = parse_rows(body)
            domains = {d for d, _, _ in parsed}
            record.update({"status": status, "bytes": len(body), "rows": len(parsed), "domains": len(domains), "content_type": content_type})
            for domain, rank, snippet in parsed:
                all_rows.append({"category": category, "competitor": competitor, "query": query, "confidence": confidence, "domain": domain, "publicwww_rank": rank, "snippet": snippet})
        except urllib.error.HTTPError as exc:
            body = exc.read() if hasattr(exc, "read") else b""
            filename.write_bytes(body)
            record.update({"status": exc.code, "bytes": len(body), "error": str(exc)})
        except Exception as exc:
            record["error"] = f"{type(exc).__name__}: {exc}"
        statuses.append(record)
        print(f"{index}/{len(QUERIES)} {category}/{competitor}: status={record['status']} domains={record.get('domains', 0)} bytes={record['bytes']}", flush=True)
        time.sleep(0.35)

    with RAW_OUT.open("w", newline="", encoding="utf-8") as handle:
        fields = ["category", "competitor", "query", "confidence", "domain", "publicwww_rank", "snippet"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(all_rows)

    # One row per website. Keep all competitor/query evidence in the same row.
    grouped = defaultdict(list)
    for row in all_rows:
        grouped[row["domain"]].append(row)
    with DEDUP_OUT.open("w", newline="", encoding="utf-8") as handle:
        fields = ["domain", "competitors", "categories", "queries", "confidences", "publicwww_ranks", "fingerprint_snippets"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for domain in sorted(grouped):
            rows = grouped[domain]
            writer.writerow({
                "domain": domain,
                "competitors": " ; ".join(sorted({r["competitor"] for r in rows})),
                "categories": " ; ".join(sorted({r["category"] for r in rows})),
                "queries": " ; ".join(sorted({r["query"] for r in rows})),
                "confidences": " ; ".join(sorted({r["confidence"] for r in rows})),
                "publicwww_ranks": " ; ".join(sorted({r["publicwww_rank"] for r in rows})),
                "fingerprint_snippets": " || ".join(sorted({r["snippet"] for r in rows if r["snippet"]})[:20]),
            })

    STATUS_OUT.write_text(json.dumps(statuses, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {RAW_OUT.name}, {DEDUP_OUT.name}, {STATUS_OUT.name}; raw_rows={len(all_rows)} unique_sites={len(grouped)}", flush=True)


if __name__ == "__main__":
    main()
