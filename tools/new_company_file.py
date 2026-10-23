#!/usr/bin/env python3
"""Create applications/APP-0NN-posting.md and make sure applications/APP-0NN.md has every standard section.

Usage: python3 tools/new_company_file.py APP-0NN posting.txt [--force]   (posting.txt = job text as published, '-' = stdin)
       python3 tools/new_company_file.py APP-0NN --stub                  (no text yet: writes a clearly marked stub)

- Refuses to overwrite an existing posting file unless --force.
- Fails when no posting text is given, unless --stub.
- If the app has no detail path (or its file is missing), creates applications/APP-0NN.md from the engine's templates/applications/TEMPLATE.md
  and records the path in data/applications.json.
- Adds each missing section by its own heading: Open questions for round 1, Posting, Contacts, Interview log,
  Outcome, Learnings. Existing content is never changed (except the old 'APP-###-posting.md' placeholder).
Works on the active tenant (tools/tenant.py).
"""
import argparse, datetime, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ledger_set as L

ROOT = L.ROOT
TABLE = "| Date | Round | With | Topics asked | What we said | Next step |\n| --- | --- | --- | --- | --- | --- |\n"
STUB_TEXT = "(STUB: job text not captured yet. Paste the posting as published here before applying.)"


def sections(app_id):
    return [
        ("Open questions for round 1", "- \n"),
        ("Posting", f"See {app_id}-posting.md (job text as published).\n"),
        ("Contacts", "- \n"),
        ("Interview log", TABLE),
        ("Outcome", "- Status: \n- Date: \n- Reason: \n- What to improve: \n"),
        ("Learnings", "- \n"),
    ]


def has_heading(t, name):
    return re.search(rf"(?mi)^##\s+{re.escape(name)}\s*$", t) is not None


def add_missing(t, app_id):
    added = []
    for name, body in sections(app_id):
        if not has_heading(t, name):
            t = t.rstrip("\n") + f"\n\n## {name}\n{body}"
            added.append(name)
    return t.replace("APP-###-posting.md", f"{app_id}-posting.md"), added


def from_template(app, app_id):
    tp = os.path.join(L.ENGINE, "templates", "applications", "TEMPLATE.md")
    if not os.path.isfile(tp):
        sys.exit("error: templates/applications/TEMPLATE.md is missing from the engine; pull the latest engine")
    with open(tp, encoding="utf-8") as f:
        t = f.read()
    t = t.replace("APP-###", app_id).replace("{Company}", app.get("company", "")).replace("{Role}", app.get("role", ""))
    fills = {"Status": app.get("status") or "Shortlisted", "Date found": app.get("dateFound", ""),
             "Date applied": app.get("dateApplied", ""), "URL": app.get("link", ""),
             "Location / mode": f"{app.get('location', '')} / {app.get('mode', '')}".strip(" /"),
             "Salary (stated or unknown)": app.get("pay", "") or "unknown", "Category": app.get("category", "")}
    for k, v in fills.items():
        t = re.sub(rf"(?m)^- {re.escape(k)}:.*$", lambda m: f"- {k}: {v}".rstrip(), t, count=1)
    return t


def read_posting(src):
    try:
        return sys.stdin.read() if src == "-" else open(src, encoding="utf-8").read()
    except OSError as e:
        sys.exit(f"error: cannot read posting text: {e}")


def main():
    ap = argparse.ArgumentParser(description="Create posting file and company-file sections for an application.")
    ap.add_argument("app_id"); ap.add_argument("posting", nargs="?")
    ap.add_argument("--force", action="store_true"); ap.add_argument("--stub", action="store_true")
    a = ap.parse_args()
    d = L.load_apps()
    app = next((x for x in d["apps"] if x["id"] == a.app_id), None)
    if app is None:
        sys.exit(f"error: {a.app_id} is not in data/applications.json")
    if a.posting:
        body = read_posting(a.posting).strip()
        if not body:
            sys.exit("error: the posting text is empty")
    elif a.stub:
        body = STUB_TEXT
    else:
        sys.exit("error: no posting text given. Pass a file (or '-' for stdin), or --stub to write a marked stub.")
    pp = L.path(f"applications/{a.app_id}-posting.md")
    if os.path.exists(pp) and not a.force:
        sys.exit(f"error: {os.path.relpath(pp, ROOT)} already exists; use --force to overwrite it. Nothing was changed.")

    detail = (app.get("detail") or "").strip()
    created = False
    if detail and os.path.isfile(L.path(detail)):
        with open(L.path(detail), encoding="utf-8") as f:
            t = f.read()
    else:
        detail = detail or f"applications/{a.app_id}.md"
        t = from_template(app, a.app_id)
        created = True
    t, added = add_missing(t, a.app_id)

    posting = (f"# {a.app_id} posting as published: {app['company']} : {app['role']}\n\n- Source: {app.get('link', '')}\n"
               f"- Captured: {datetime.date.today()}\n- Location / mode: {app.get('location', '')} / {app.get('mode', '')}\n"
               f"- Pay as posted: {app.get('pay', '')}\n\n## Job text\n\n{body}\n")
    L.atomic_write(pp, posting)
    L.atomic_write(L.path(detail), t)
    if app.get("detail") != detail:
        app["detail"] = detail
        L.atomic_write(L.path("data/applications.json"), L.dump_apps(d))
    print(f"ok {a.app_id}: wrote {os.path.relpath(pp, ROOT)}; "
          + (f"created {detail} from template; " if created else "") + ("added sections: " + ", ".join(added) if added else "no sections missing")
          + ("; STUB posting, fill it in before applying" if body == STUB_TEXT else ""))


if __name__ == "__main__":
    main()
