#!/usr/bin/env python3
"""Record a submitted application: update data/applications.json, the APP company file and the ledger CSV,
rebuild the board, then commit (and push only when asked).

Usage: python3 tools/record_application.py APP-003 answers.json [--dry-run] [--force] [--push] [--no-commit]
answers.json: {"date": "2026-10-21", "via": "Greenhouse form on databricks.com", "answers": [["Field","Answer"],...],
               "cover_note": "...", "confirmation": "text shown after submit", "notes": "optional",
               "status": "Applied" (optional)}

Pre-flight (nothing is written if any check fails): the app exists, its detail file exists, the app is not already
Applied (or later) unless --force, the date is valid, the answers have the right shape, the CSV header is the new schema.
Default is commit without push. Push with --push or env JOBS_PUSH=1 (runs git pull --rebase --autostash first).
Only the files this tool changed are added and committed. The tenant comes from tools/tenant.py. It commits only when the tenant folder is its own git repo.
"""
import argparse, datetime, json, os, re, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ledger_set as L

ROOT = L.ROOT
COAUTHOR = "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
LATER = ("Applied", "Screening", "Interview", "Offer", "Rejected", "Withdrawn")
COVER_PLACEHOLDERS = ("", "(text as sent)", "None submitted.")


def fail(msg):
    sys.exit("error: " + msg + "\nNothing was written.")


# ---- pre-flight --------------------------------------------------------------
def parse_date(s):
    try:
        return datetime.datetime.strptime(str(s), "%Y-%m-%d").date()
    except ValueError:
        return None


def preflight(app_id, r, force, d, vocab):
    app = next((x for x in d.get("apps", []) if x.get("id") == app_id), None)
    if app is None:
        fail(f"{app_id} is not in data/applications.json")
    day = parse_date(r.get("date"))
    if day is None:
        fail(f"answers.json 'date' must be YYYY-MM-DD, got {r.get('date')!r}")
    if day > datetime.date.today() + datetime.timedelta(days=1) and not force:
        fail(f"date {day} is in the future (use --force if intended)")
    detail = (app.get("detail") or "").strip()
    if not detail:
        fail(f"{app_id} has no detail path. Run: python3 tools/new_company_file.py {app_id} posting.txt")
    dp = os.path.normpath(os.path.join(ROOT, detail))
    if not dp.startswith(os.path.normpath(ROOT) + os.sep):
        fail(f"detail path {detail} points outside the repo")
    if not os.path.isfile(dp):
        fail(f"detail file {detail} does not exist. Run: python3 tools/new_company_file.py {app_id} posting.txt")
    new_status = r.get("status", "Applied")
    if new_status not in vocab["app_status"]:
        fail(f"status '{new_status}' is not an app status ({', '.join(vocab['app_status'])})")
    if app.get("status") in LATER and not force:
        fail(f"{app_id} is already {app['status']} (applied {app.get('dateApplied') or 'unknown date'}); use --force to re-record")
    ans = r.get("answers", [])
    if not isinstance(ans, list) or any(not isinstance(p, (list, tuple)) or len(p) != 2 for p in ans):
        fail("'answers' must be a list of [field, answer] pairs")
    for k in ("via", "confirmation"):
        if not str(r.get(k, "")).strip():
            fail(f"answers.json needs a non-empty '{k}'")
    return app, day, dp, new_status


# ---- company file text edits -------------------------------------------------
def cell(s):
    return str(s).replace("|", "\\|").replace("\r", "").replace("\n", " ").strip()


TABLE_RE = re.compile(r"(\|\s*Field\s*\|\s*Answer\s*\|[ \t]*\n\|\s*-+\s*\|\s*-+\s*\|[ \t]*\n?)")


def set_line(t, label, value):
    """Replace '- label: ...' (first match). Return (text, found)."""
    new, n = re.subn(rf"(?m)^- {re.escape(label)}:.*$", lambda m: f"- {label}: {value}", t, count=1)
    return new, n > 0


def edit_company_file(t, app, status, day, r):
    t, ok = set_line(t, "Status", status)
    if not ok:
        t = t.rstrip("\n") + f"\n\n- Status: {status}\n"
    t, ok = set_line(t, "Date applied", str(day))
    if not ok:
        t = t.rstrip("\n") + f"\n- Date applied: {day}\n"
    rows = [f"| {cell(k)} | {cell(v)} |" for k, v in r.get("answers", [])]
    rows = [x for x in rows if x not in t]
    if rows:
        block = "\n".join(rows) + "\n"
        m = TABLE_RE.search(t)
        if m:
            end = m.end()
            if not m.group(1).endswith("\n"):
                t = t[:end] + "\n" + t[end:]
                end += 1
            t = t[:end] + block + t[end:]
        else:
            t = t.rstrip("\n") + "\n\n## Submitted answers\n\n| Field | Answer |\n| --- | --- |\n" + block
    cover = (r.get("cover_note") or "").strip() or "None submitted."
    m = re.search(r"(?m)^## Cover note[ \t]*\n(.*?)(?=^## |\Z)", t, re.S)
    if m is None:
        t = t.rstrip("\n") + f"\n\n## Cover note\n{cover}\n"
    elif m.group(1).strip() in COVER_PLACEHOLDERS:
        t = t[:m.start(1)] + cover + "\n\n" + t[m.end(1):]
    elif cover not in m.group(1):
        t = t[:m.end(1)].rstrip("\n") + f"\n\nCover note as sent on {day}:\n{cover}\n\n" + t[m.end(1):]
    due = day + datetime.timedelta(days=7)
    t = t.rstrip("\n") + (f"\n\n## Submission record ({day})\n- Submitted via: {r['via']}\n"
                          f"- Confirmation: {r['confirmation']}\n- Follow-up check due: {due}\n")
    return t


# ---- git ---------------------------------------------------------------------
def git(*args, check=True):
    return subprocess.run(["git", *args], cwd=ROOT, check=check, capture_output=True, text=True)


def in_git_repo():
    p = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=ROOT, capture_output=True, text=True)
    return p.returncode == 0 and os.path.realpath(p.stdout.strip()) == os.path.realpath(ROOT)


def commit_and_push(paths, app_id, company, push):
    rel = [os.path.relpath(p, ROOT) for p in paths]
    git("add", "--", *rel)
    msg = f"Record application {app_id} ({company})\n\n{COAUTHOR}"
    meta = L.tenant.tenant_meta(ROOT)
    ident = []
    if meta.get("git_name") and meta.get("git_email"):
        ident = ["-c", f"user.name={meta['git_name']}", "-c", f"user.email={meta['git_email']}"]
    git(*ident, "commit", "-q", "-m", msg, "--", *rel)
    print("committed:", ", ".join(rel))
    if not push:
        print("not pushed (use --push or JOBS_PUSH=1)")
        return
    pull = git("pull", "--rebase", "--autostash", check=False)
    if pull.returncode != 0:
        print("COMMIT IS SAFE LOCALLY, push skipped: git pull --rebase failed:\n" + pull.stderr.strip() +
              "\nRecovery: resolve with 'git rebase --abort' or fix conflicts, then run 'git push origin main'.")
        return
    branch = git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip() or "main"
    ps = git("push", "-q", "origin", branch, check=False)
    if ps.returncode != 0:
        print("COMMIT IS SAFE LOCALLY, push failed:\n" + ps.stderr.strip() + "\nRecovery: run 'git push' once the problem is fixed.")
    else:
        print("pushed")


# ---- main --------------------------------------------------------------------
def build_changes(app_id, r, force, vocab):
    d = L.load_apps()
    app, day, dp, new_status = preflight(app_id, r, force, d, vocab)
    ledger_ok = os.path.exists(L.path("data/seen-jobs.csv"))
    rows = L.read_ledger(vocab) if ledger_ok else None   # exits with a clear message on an old header
    changes = {}  # path -> new text
    with open(dp, encoding="utf-8") as f:
        changes[dp] = edit_company_file(f.read(), app, new_status, day, r)
    app["status"] = new_status
    app["dateApplied"] = str(day)
    if r.get("notes"):
        app["notes"] = (app.get("notes", "") + " " + r["notes"]).strip()
    fu = app.get("followUp") if isinstance(app.get("followUp"), dict) else {}
    fu["nextCheck"] = str(day + datetime.timedelta(days=7))
    fu.setdefault("lastCheck", "")
    app["followUp"] = fu
    if "blocker" in app:
        app["blocker"] = ""
    d["updated"] = str(datetime.date.today())
    changes[L.path("data/applications.json")] = L.dump_apps(d)
    ledger_note = "no data/seen-jobs.csv"
    if rows is not None:
        row = L.find_row_for_app(rows, app)
        if row is None:
            ledger_note = "no ledger row found for this app (add one with ledger_set.py --add --app-id)"
        else:
            L.apply_update(vocab, rows, row["job_id"], status="Applied", app_id=app_id)
            changes[L.path("data/seen-jobs.csv")] = L.ledger_text(rows, vocab)
            ledger_note = f"ledger row {row['job_id']} -> Applied"
    return app, changes, ledger_note


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("app_id"); ap.add_argument("answers")
    ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--force", action="store_true")
    ap.add_argument("--push", action="store_true"); ap.add_argument("--no-commit", action="store_true")
    a = ap.parse_args()
    push = a.push or os.environ.get("JOBS_PUSH") == "1"
    try:
        with open(a.answers, encoding="utf-8") as f:
            r = json.load(f)
    except (OSError, ValueError) as e:
        fail(f"cannot read {a.answers}: {e}")
    vocab = L.load_vocab()
    app, changes, ledger_note = build_changes(a.app_id, r, a.force, vocab)
    print(f"pre-flight ok for {a.app_id} ({app['company']}); {ledger_note}")
    if a.dry_run:
        for p in changes:
            print("would write", os.path.relpath(p, ROOT))
        print("would rebuild board/index.html and applications-ledger.md; would commit" + (" and push" if push else ", no push"))
        return
    backups = {}
    try:
        for p, text in changes.items():
            backups[p] = open(p, encoding="utf-8").read() if os.path.exists(p) else None
            L.atomic_write(p, text)
        for gp in (L.path("board/index.html"), L.path("applications-ledger.md")):
            backups[gp] = open(gp, encoding="utf-8").read() if os.path.exists(gp) else None
        build_script = os.path.join(L.TOOLS_DIR, "build_board.py")
        subprocess.run([sys.executable, build_script], check=True, env={**os.environ, "JOBS_ROOT": ROOT}, stdout=subprocess.DEVNULL)
    except BaseException as e:
        for p, old in backups.items():
            if old is not None:
                L.atomic_write(p, old)
        sys.exit(f"error: failed before commit ({e}). Files were restored; nothing is committed. Fix the cause and re-run.")
    paths = list(changes) + [L.path("board/index.html"), L.path("applications-ledger.md")]
    paths = [p for p in paths if os.path.exists(p)]
    print("recorded", a.app_id)
    if a.no_commit or not in_git_repo():
        print("files updated; not committed" + ("" if in_git_repo() else " (not a git repo)"))
        return
    try:
        commit_and_push(paths, a.app_id, app["company"], push)
    except subprocess.CalledProcessError as e:
        print("RECORDED BUT NOT COMMITTED: git failed: " + (e.stderr or str(e)).strip() +
              "\nRecovery: the files are already updated. Run: git add -- " + " ".join(os.path.relpath(p, ROOT) for p in paths) +
              " && git commit -m 'Record application " + a.app_id + "'")
        sys.exit(2)


if __name__ == "__main__":
    main()
