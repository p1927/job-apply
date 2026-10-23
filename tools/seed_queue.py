#!/usr/bin/env python3
"""Add LinkedIn job-search pages to the active tenant's data/search-queue.json (one entry per query x location x page).

Usage: python3 tools/seed_queue.py --category Local --location Sweden --query "AI Engineer" --query "ML Engineer" [--pages 2] [--recent 2592000]
Entries that already exist (same category, query, location, start) are skipped, so it is safe to re-run.
Categories must exist in the vocabulary. New entries have status 'pending'; ids continue from the highest q### in the file.
"""
import argparse
import datetime
import json
import os
import re
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tenant
import ledger_set as L


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--category", required=True)
    ap.add_argument("--location", required=True)
    ap.add_argument("--query", action="append", required=True)
    ap.add_argument("--pages", type=int, default=2, help="pages of 25 results per query (default 2)")
    ap.add_argument("--recent", type=int, default=2592000, help="only jobs posted in the last N seconds (default 30 days)")
    a = ap.parse_args()
    vocab = tenant.load_vocab()
    if a.category not in vocab["categories"]:
        sys.exit(f"error: category '{a.category}' is not in the vocabulary: {', '.join(vocab['categories'])}")
    p = L.path("data/search-queue.json")
    doc = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {"updated": "", "queue": []}
    q = doc.setdefault("queue", [])
    have = {(e.get("category"), e.get("query"), e.get("location"), e.get("start")) for e in q}
    top = max([int(m.group(1)) for e in q if (m := re.fullmatch(r"q(\d+)", str(e.get("id", ""))))] or [0])
    added = 0
    for query in a.query:
        for page in range(a.pages):
            start = page * 25
            if (a.category, query, a.location, start) in have:
                continue
            top += 1
            params = urllib.parse.urlencode({"keywords": query, "location": a.location, "f_TPR": f"r{a.recent}", "start": start})
            q.append({"id": f"q{top:03d}", "category": a.category, "query": query, "location": a.location,
                      "filters": {"f_TPR": f"r{a.recent}"}, "start": start, "status": "pending",
                      "url": "https://www.linkedin.com/jobs/search/?" + params, "notes": ""})
            added += 1
    doc["updated"] = str(datetime.date.today())
    L.atomic_write(p, json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    print(f"added {added} queue entries ({len(q)} total)")


if __name__ == "__main__":
    main()
