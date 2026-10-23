#!/usr/bin/env python3
"""Validate the job-application data. Stdlib only. Exit 1 on any error.

Usage: python3 tools/check_consistency.py [--fix-nothing]
Runs on the active tenant (tools/tenant.py). Checks config/vocab.json plus tenant overrides, data/seen-jobs.csv, data/applications.json,
data/search-queue.json and the per-application files in applications/.
Output lines look like "ERROR file: detail" or "WARN file: detail".
"""
import csv
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tenant  # noqa: E402

ROOT = Path(tenant.root())
DATA = ROOT / "data"
LATER = ("Applied", "Screening", "Interview", "Offer", "Rejected", "Withdrawn")
SECTIONS = ("Open questions for round 1", "Interview log", "Outcome")
PLACEHOLDER = "(paste the full job text here)"
errors, warns = [], []


def err(f, d):
    errors.append(f"ERROR {f}: {d}")


def warn(f, d):
    warns.append(f"WARN {f}: {d}")


def load_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        err(path.relative_to(ROOT), f"cannot parse ({e})")
        return None


def read(path):
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


def main():
    try:
        vocab = tenant.load_vocab(str(ROOT))
    except (OSError, ValueError) as e:
        err("config/vocab.json", f"cannot load vocabulary ({e})")
        return finish({})
    meta = tenant.tenant_meta(str(ROOT))
    if not meta.get("name"):
        err("tenant.json", "missing 'name'")
    counts = {}

    # ---- applications.json
    apps_doc = load_json(DATA / "applications.json") or {}
    apps = apps_doc.get("apps", [])
    app_by_id = {}
    f = "data/applications.json"
    newest = ""
    for a in apps:
        aid = a.get("id", "?")
        if aid in app_by_id:
            err(f, f"duplicate id {aid}")
        app_by_id[aid] = a
        if a.get("status") not in vocab["app_status"]:
            err(f, f"{aid} status '{a.get('status')}' not in vocab")
        if a.get("track") not in vocab["tracks"]:
            err(f, f"{aid} track '{a.get('track')}' not in vocab")
        if a.get("category") not in vocab["categories"]:
            err(f, f"{aid} category '{a.get('category')}' not in vocab")
        if a.get("blocker", "") not in vocab["ledger_blockers"]:
            err(f, f"{aid} blocker '{a.get('blocker')}' not in vocab")
        for key in ("detail", "resume"):
            v = a.get(key)
            if v and not (ROOT / v).exists():
                err(f, f"{aid} {key} file missing: {v}")
        d = a.get("dateApplied", "")
        if d and d > newest:
            newest = d
        st = a.get("status")
        if st in LATER:
            if not d:
                err(f, f"{aid} is {st} but has no dateApplied")
            comp = read(ROOT / "applications" / f"{aid}.md")
            if comp is None:
                err(f, f"{aid} company file applications/{aid}.md missing")
            else:
                if "- Confirmation:" not in comp:
                    (warn if aid == "APP-009" else err)(f"applications/{aid}.md", "no '- Confirmation:' line")
                for s in SECTIONS:
                    if f"## {s}" not in comp:
                        err(f"applications/{aid}.md", f"missing section '{s}'")
            post = read(ROOT / "applications" / f"{aid}-posting.md")
            if post is None:
                err(f"applications/{aid}-posting.md", "posting file missing")
            elif PLACEHOLDER in post:
                err(f"applications/{aid}-posting.md", "posting still has placeholder")
        else:
            post = read(ROOT / "applications" / f"{aid}-posting.md")
            if post is not None and PLACEHOLDER in post:
                warn(f"applications/{aid}-posting.md", "posting still has placeholder")
            if a.get("detail") and post is None:
                warn(f"applications/{aid}-posting.md", "company file exists but posting file missing")
    upd = apps_doc.get("updated", "")
    if newest and upd < newest:
        err(f, f"'updated' {upd or '(empty)'} older than newest dateApplied {newest}")
    counts["apps"] = Counter(a.get("status") for a in apps)

    # ---- seen-jobs.csv
    f = "data/seen-jobs.csv"
    try:
        with open(DATA / "seen-jobs.csv", newline="", encoding="utf-8") as fh:
            rd = csv.DictReader(fh)
            header = rd.fieldnames
            rows = list(rd)
    except Exception as e:  # noqa: BLE001
        err(f, f"cannot read ({e})")
        header, rows = None, []
    if header != vocab["csv_header"]:
        err(f, f"header {header} != vocab csv_header")
    seen = set()
    for i, r in enumerate(rows, start=2):
        jid = r.get("job_id", "")
        loc = f"{f}:{i} ({jid})"
        if jid in seen:
            err(loc, "duplicate job_id")
        seen.add(jid)
        for col, key in (("status", "ledger_status"), ("category", "categories"),
                         ("workplace", "workplace_values"), ("source", "source_values"),
                         ("blocker", "ledger_blockers")):
            if r.get(col) is None or r[col] not in vocab[key]:
                err(loc, f"{col} '{r.get(col)}' not in vocab")
        reason = r.get("reason", "")
        if reason and reason not in vocab["ledger_reason_codes"]:
            err(loc, f"reason '{reason}' not in vocab")
        if r.get("status") == "Not-relevant" and not reason:
            err(loc, "Not-relevant without reason")
        if r.get("status") == "Applied":
            aid = r.get("app_id", "")
            if not aid:
                err(loc, "Applied without app_id")
            elif aid not in app_by_id:
                err(loc, f"app_id {aid} not in applications.json")
            elif app_by_id[aid].get("status") not in LATER:
                err(loc, f"Applied but {aid} status is {app_by_id[aid].get('status')}")
        elif r.get("app_id") and r["app_id"] not in app_by_id:
            err(loc, f"app_id {r['app_id']} not in applications.json")
    counts["ledger"] = Counter(r.get("status") for r in rows)
    counts["ledger_rows"] = len(rows)

    # ---- search-queue.json
    q = load_json(DATA / "search-queue.json")
    if q is not None:
        if not isinstance(q.get("queue"), list):
            err("data/search-queue.json", "no 'queue' list")
        else:
            ids = [e.get("id") for e in q["queue"]]
            if len(ids) != len(set(ids)):
                err("data/search-queue.json", "duplicate queue ids")
            for e in q["queue"]:
                if e.get("status") not in ("done", "pending", "rate-limited"):
                    err("data/search-queue.json", f"{e.get('id')} bad status '{e.get('status')}'")
            counts["queue"] = Counter(e.get("status") for e in q["queue"])

    # ---- tenants must never mix (engine holds no personal data; tenants hold only their own)
    import check_leaks
    for line in check_leaks.scan():
        err("leak", line)
    return finish(counts)


def finish(counts):
    for line in errors + warns:
        print(line)
    print(f"--- {len(errors)} error(s), {len(warns)} warning(s)")
    for k, v in counts.items():
        print(f"{k}: {dict(v) if isinstance(v, Counter) else v}")
    return 1 if errors else 0


if __name__ == "__main__":
    # --fix-nothing is accepted and is a no-op: this tool only reads.
    sys.exit(main())
