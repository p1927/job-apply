#!/usr/bin/env python3
"""Coverage check: did every job seen in a source (email alert, LinkedIn search page, board) reach the ledger?

Usage:
  coverage.py ITEMS.json|ITEMS.tsv|- [--add] [--source linkedin|company|board|...] [--category CAT]
  coverage.py --queue            (progress of data/search-queue.json by category and status)
  coverage.py --report           (ledger totals and how many rows came from each source)

ITEMS.tsv (or "-" for stdin) holds one job per line: id<TAB>company<TAB>title<TAB>location.
ITEMS.json is a list of {"linkedin_job_id"|"job_id": "...", "company": "...", "title": "...", "location": "...",
"source": "..."} objects, harvested from Gmail alerts or a LinkedIn results page. An item counts as covered when its id is
in data/seen-jobs.csv OR its normalised company + title matches a row (the ledger also holds company-site ids such as
tv4-8259879, so ids alone miss jobs). With --add every uncovered item becomes a `New` ledger row so the review loop sees it.
Prints: items, covered, missing, then one line per missing item. Exit 0 always; the missing count is the score.
"""
import argparse, csv, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tenant
import ledger_set as L


def norm(s):
    s = (s or "").lower()
    s = re.sub(r"\b(ab|inc|ltd|gmbh|group|the|nordic|sweden|sverige)\b", " ", s)
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def ledger_rows():
    with open(L.path("data/seen-jobs.csv"), encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def key(company, title):
    return norm(company) + "|" + norm(title)


def same(a, b):
    """Same job when the titles match after normalising and one company name contains the other ('Wolt' vs 'Wolt (DoorDash)')."""
    ca, ta = a.split("|"); cb, tb = b.split("|")
    return ta == tb and ta != "" and (ca == cb or ca in cb or cb in ca)


def check(items, rows):
    ids = {r["job_id"] for r in rows if r.get("status") != "New" or True}
    keys = [key(r["company"], r["title"]) for r in rows]
    covered, missing = [], []
    for it in items:
        jid = str(it.get("linkedin_job_id") or it.get("job_id") or "")
        k = key(it.get("company"), it.get("title"))
        (covered if (jid and jid in ids) or any(same(k, x) for x in keys) else missing).append(it)
    return covered, missing


def queue_report():
    p = L.path("data/search-queue.json")
    q = json.load(open(p, encoding="utf-8")).get("queue", [])
    by = {}
    for e in q:
        by.setdefault(e.get("category"), {}).setdefault(e.get("status"), 0)
        by[e["category"]][e["status"]] += 1
    done = sum(v.get("done", 0) for v in by.values())
    print(f"search queue: {done}/{len(q)} done")
    for c, v in sorted(by.items()):
        print(f"  {c}: " + ", ".join(f"{k} {n}" for k, n in sorted(v.items())))
    return done, len(q)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("items", nargs="?")
    ap.add_argument("--add", action="store_true")
    ap.add_argument("--source", default="linkedin")
    ap.add_argument("--category", default="Other")
    ap.add_argument("--queue", action="store_true")
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()
    rows = ledger_rows()
    if a.queue:
        queue_report()
    if a.report:
        cnt = {}
        for r in rows:
            cnt[r["status"]] = cnt.get(r["status"], 0) + 1
        src = {}
        for r in rows:
            src[r["source"]] = src.get(r["source"], 0) + 1
        print("ledger:", cnt, "| by source:", src)
    if not a.items:
        return
    if a.items.endswith(".tsv") or a.items == "-":
        raw = sys.stdin.read() if a.items == "-" else open(a.items, encoding="utf-8").read()
        items = []
        for ln in raw.splitlines():
            f = [x.strip() for x in ln.split("\t")]
            if len(f) >= 3 and f[0] and f[1] != "undefined":
                items.append({"linkedin_job_id": f[0], "company": f[1], "title": f[2], "location": f[3] if len(f) > 3 else ""})
    else:
        items = json.load(open(a.items, encoding="utf-8"))
    covered, missing = check(items, rows)
    print(f"items {len(items)}  covered {len(covered)}  missing {len(missing)}")
    for it in missing:
        jid = it.get("linkedin_job_id") or it.get("job_id") or ""
        print(f"  MISSING {jid} | {it.get('company')} | {it.get('title')} | {it.get('location')}")
    if a.add:
        import subprocess
        for it in missing:
            jid = str(it.get("linkedin_job_id") or it.get("job_id") or "")
            if not jid:
                print("  skip (no id):", it.get("company"), it.get("title"))
                continue
            cmd = [sys.executable, os.path.join(L.TOOLS_DIR, "ledger_set.py"), jid, "--add", "--company", it.get("company") or "?",
                   "--title", it.get("title") or "?", "--location", it.get("location") or "", "--category", a.category,
                   "--source", it.get("source_vocab") or a.source, "--status", "New"]
            r = subprocess.run(cmd, capture_output=True, text=True)
            print("  added" if r.returncode == 0 else "  FAILED " + r.stderr.strip()[-120:], jid)


if __name__ == "__main__":
    main()
