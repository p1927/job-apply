#!/usr/bin/env python3
"""Allocate the next APP id and add the app to data/applications.json in one locked step (safe with parallel agents).
Never pick an APP id by hand and never edit applications.json by hand to add an app: use this tool.

Usage: python3 tools/new_app.py --company Acme --role "AI Engineer" --link URL [--category Remote] [--track ai_remote]
         [--location L] [--mode M] [--pay P] [--job-id 123456]   (job-id links the ledger row to the new app)
Prints the new id on the last line (APP-115). A company+role that already has an app in Applied or later is refused
unless --force; a company+role that is still Shortlisted returns that existing id instead of making a second one.
The new app carries every key the live applications.json uses (see new_app_record)."""
import argparse, datetime, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ledger_set as L
import datalock


def new_app_record(app_id, a, today):
    """One app with the same keys as the existing apps in data/applications.json."""
    return {"id": app_id, "company": a["company"], "role": a["role"], "track": a.get("track") or "", "location": a.get("location") or "",
            "mode": a.get("mode") or "", "bigTech": False, "fit": "weak", "pay": a.get("pay") or "", "checks": [], "learn": [],
            "link": a["link"], "links": [], "resume": "", "detail": "", "status": "Shortlisted", "dateFound": today,
            "dateApplied": "", "notes": "", "tag": "", "verdict": "check", "category": a.get("category") or "Other", "blocker": ""}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for k in ("company", "role", "link"):
        ap.add_argument("--" + k, required=True)
    for k in ("category", "track", "location", "mode", "pay"):
        ap.add_argument("--" + k)
    ap.add_argument("--job-id", dest="job_id")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args(argv)
    vocab = L.load_vocab()
    if a.category and a.category not in vocab["categories"]:
        L.die(f"category '{a.category}' is not in vocab ({', '.join(vocab['categories'])})")
    if a.track and a.track not in vocab["tracks"]:
        L.die(f"track '{a.track}' is not in vocab ({', '.join(vocab['tracks'])})")
    today = os.environ.get("JOBS_TODAY") or str(datetime.date.today())
    with L.locked():
        d = L.load_apps()
        same = [x for x in d["apps"] if datalock.norm(x.get("company")) == datalock.norm(a.company)
                and datalock.norm(x.get("role")) == datalock.norm(a.role)]
        if same and not a.force:
            x = same[0]
            if x.get("status") == "Shortlisted":
                print(f"exists {x['id']} (Shortlisted); reuse it")
                print(x["id"])
                return
            L.die(f"{x['id']} already covers {a.company} / {a.role} ({x.get('status')}); use --force if the roles differ")
        new_id = datalock.next_app_id(d["apps"])
        d["apps"].append(new_app_record(new_id, vars(a), today))
        d["updated"] = today
        rows = None
        if a.job_id:   # validate the ledger link before anything is written
            rows = L.read_ledger(vocab)
            L.apply_update(vocab, rows, a.job_id, app_id=new_id)
        L.atomic_write(L.path("data/applications.json"), L.dump_apps(d))
        if rows is not None:
            L.save_ledger(rows, vocab)
    print(new_id)


if __name__ == "__main__":
    main()
