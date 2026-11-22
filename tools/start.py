#!/usr/bin/env python3
"""One call at "find jobs" or "apply": prints the state of the active person's job search in short bullets and a Next line.
Read only. Usage: python3 tools/start.py [--no-check]   (--no-check skips the consistency run)"""
import collections, datetime, json, os, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ledger_set as L


def main(argv):
    vocab = L.load_vocab()
    rows = L.read_ledger(vocab) if os.path.exists(L.path("data/seen-jobs.csv")) else []
    apps = L.load_apps().get("apps", []) if os.path.exists(L.path("data/applications.json")) else []
    c = collections.Counter(r["status"] for r in rows)
    today = os.environ.get("JOBS_TODAY") or str(datetime.date.today())
    due = [a["id"] for a in apps if a.get("status") in ("Applied", "Screening")
           and (a.get("followUp") or {}).get("nextCheck") and a["followUp"]["nextCheck"] <= today]
    blocked = [a["id"] for a in apps if a.get("blocker")]
    try:
        with open(L.path("data/search-queue.json"), encoding="utf-8") as f:
            q = [e for e in json.load(f).get("queue", []) if e.get("status") == "pending"]
    except (OSError, ValueError):
        q = []
    problems = "skipped"
    if "--no-check" not in argv:
        p = subprocess.run([sys.executable, os.path.join(L.TOOLS_DIR, "check_consistency.py")], capture_output=True, text=True,
                           env={**os.environ, "JOBS_ROOT": L.ROOT})
        last = [ln for ln in p.stdout.splitlines() if ln.startswith("---")]
        problems = last[0].lstrip("- ") if last else "could not run"
    print(f"- tenant: {os.path.basename(L.ROOT)}")
    print(f"- data check: {problems}")
    print(f"- ledger: {c['New']} New to review, {c['Relevant']} Relevant to apply")
    print(f"- blocked on you: {', '.join(blocked) or 'none'}")
    print(f"- follow-ups due: {', '.join(due) or 'none'}")
    print(f"- search queue: {len(q)} pending" + (f", next {q[0].get('url', '')}" if q else ""))
    nxt = ("fix the data check errors" if " 0 error" not in " " + problems and problems not in ("skipped", "could not run")
           else "review New rows" if c["New"] else "apply to Relevant rows" if c["Relevant"]
           else "run the next search page" if q else "seed the search queue")
    print("- Next: " + nxt)


if __name__ == "__main__":
    main(sys.argv[1:])
