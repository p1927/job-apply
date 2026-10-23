#!/usr/bin/env python3
"""Update (or add) one row of data/seen-jobs.csv, validated against config/vocab.json (plus the tenant's data/vocab.overrides.json).

Usage:
  ledger_set.py JOB_ID --status S [--reason CODE] [--blocker B] [--app-id APP-0NN]
                [--note TEXT] [--category C] [--workplace W] [--source S]
  ledger_set.py JOB_ID --add --company C --title T [--location L] [--workplace W] [--category C] [--source S] [--status New]
  ledger_set.py JOB_ID Status "note" [category]        (old positional form, still validated)

Rules: status/reason/blocker/category/workplace/source must be in the vocabulary. Not-relevant needs a reason.
Moving a row to Applied, Not-relevant or Closed clears its blocker unless --blocker is given (use --blocker "" to clear).
The file is written atomically (temp file, then rename), with LF line endings and UTF-8.
The tenant comes from tools/tenant.py (env JOBS_ROOT or JOBS_TENANT, else tenants/.active).
"""
import argparse, csv, io, json, os, sys, tempfile

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS_DIR)
import tenant

ROOT = tenant.root()          # this person's folder; the only place data is read from or written to
ENGINE = tenant.ENGINE        # shared tools, config and templates (never holds personal data)
DONE_STATUSES = ("Applied", "Not-relevant", "Closed")


def die(msg):
    sys.exit("error: " + msg)


def path(*parts):
    return os.path.join(ROOT, *parts)


# ---- shared helpers (also imported by record_application.py and new_company_file.py) ----
def atomic_write(p, text):
    """Write text to p via a temp file in the same directory, then os.replace. LF endings, UTF-8."""
    if not tenant.inside(p, ROOT):
        die(f"refusing to write outside the tenant folder: {p}")
    d = os.path.dirname(p) or "."
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tmp-", suffix=".part", dir=d)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, p)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def load_vocab():
    try:
        return tenant.load_vocab(ROOT)
    except (OSError, ValueError) as e:
        die(f"cannot read config/vocab.json or the tenant overrides: {e}")


def load_apps():
    with open(path("data/applications.json"), encoding="utf-8") as f:
        return json.load(f)


def dump_apps(d):
    return json.dumps(d, indent=1, ensure_ascii=False) + "\n"


def read_ledger(vocab):
    """Return (rows as list of dicts keyed by the vocab header). Exits with a clear message on an old header."""
    p = path("data/seen-jobs.csv")
    want = vocab["csv_header"]
    with open(p, encoding="utf-8", newline="") as f:
        text = f.read()
    rd = csv.DictReader(io.StringIO(text, newline=""), restkey="_extra")
    got = rd.fieldnames or []
    if got != want:
        die("data/seen-jobs.csv header is not the new schema (migration still running?).\n"
            f"  found:    {','.join(got)}\n  expected: {','.join(want)}")
    rows = []
    for r in rd:
        r.pop("_extra", None)
        rows.append({k: (r.get(k) or "") for k in want})
    return rows


def ledger_text(rows, vocab):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=vocab["csv_header"], lineterminator="\n", extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def check_vocab(vocab, status=None, reason=None, blocker=None, category=None, workplace=None, source=None):
    """Return a list of problems (empty when everything is valid). None means 'not given'."""
    checks = [("status", status, "ledger_status"), ("reason", reason, "ledger_reason_codes"),
              ("blocker", blocker, "ledger_blockers"), ("category", category, "categories"),
              ("workplace", workplace, "workplace_values"), ("source", source, "source_values")]
    bad = []
    for name, val, key in checks:
        if val is None or (val == "" and name in ("reason", "blocker")):
            continue
        if val not in vocab[key]:
            bad.append(f"{name} '{val}' is not in vocab ({', '.join(x for x in vocab[key] if x)})")
    return bad


def apply_update(vocab, rows, job_id, add=None, **f):
    """Update the row for job_id in rows (list of dicts), or add it when `add` is a dict of initial values.
    f may hold status, reason, blocker, app_id, note, category, workplace, source (None = leave unchanged).
    Returns (row, created). Raises SystemExit on invalid input."""
    problems = check_vocab(vocab, **{k: f.get(k) for k in ("status", "reason", "blocker", "category", "workplace", "source")})
    if problems:
        die("; ".join(problems))
    row = next((r for r in rows if r["job_id"] == job_id), None)
    created = False
    if row is None:
        if add is None:
            die(f"job id {job_id} not found in data/seen-jobs.csv (use --add to create it)")
        if not add.get("company") or not add.get("title"):
            die("--add needs --company and --title")
        row = {k: "" for k in vocab["csv_header"]}
        row.update({"job_id": job_id, "status": "New", "workplace": "Unknown", "category": "Other"})
        row.update({k: v for k, v in add.items() if v is not None})
        rows.append(row)
        created = True
    for k in ("status", "reason", "blocker", "app_id", "note", "category", "workplace", "source"):
        if f.get(k) is not None:
            row[k] = f[k]
    if f.get("status") in DONE_STATUSES and f.get("blocker") is None:
        row["blocker"] = ""
    if row["status"] == "Not-relevant" and not row["reason"]:
        die("status Not-relevant needs --reason (one of: " + ", ".join(vocab["ledger_reason_codes"]) + ")")
    if row["status"] not in vocab["ledger_status"]:
        die(f"row status '{row['status']}' is not in vocab")
    return row, created


def save_ledger(rows, vocab):
    atomic_write(path("data/seen-jobs.csv"), ledger_text(rows, vocab))


def link_job_ids(link):
    import re
    return re.findall(r"\d{6,}", link or "")


def find_row_for_app(rows, app):
    """Row linked by app_id, else by a job id found in the app's posting link."""
    for r in rows:
        if r["app_id"] == app["id"]:
            return r
    ids = link_job_ids(app.get("link"))
    for r in rows:
        if r["job_id"] in ids:
            return r
    return None


def sync_app_blocker(app_id, blocker):
    """Set the blocker key on the matching app in applications.json (only that key). Returns True if changed."""
    p = path("data/applications.json")
    if not os.path.exists(p):
        return False
    d = load_apps()
    app = next((a for a in d.get("apps", []) if a.get("id") == app_id), None)
    if app is None or blocker is None or app.get("blocker", "") == blocker:
        return False
    app["blocker"] = blocker
    atomic_write(p, dump_apps(d))
    return True


# ---- CLI ---------------------------------------------------------------------
def legacy_to_args(argv, vocab):
    """Map the old positional form 'JOB_ID Status "note" [category]' onto the new options, or return None."""
    pos = [a for a in argv if not a.startswith("--")]
    if len(argv) != len(pos) or len(pos) < 2 or len(pos) > 4:
        return None
    job_id, status = pos[0], pos[1]
    note = pos[2] if len(pos) > 2 else None
    cat = pos[3] if len(pos) > 3 else None
    out = [job_id]
    if status in vocab["ledger_status"]:
        out += ["--status", status]
    elif status.startswith("Skip-"):
        code = status[5:].lower()
        out += ["--status", "Not-relevant", "--reason", code if code in vocab["ledger_reason_codes"] else "other"]
        if code not in vocab["ledger_reason_codes"]:
            note = (f"{status}: {note}" if note else status)
    else:
        die(f"status '{status}' is not valid any more. Use one of: {', '.join(vocab['ledger_status'])} "
            "(Skip-X becomes Not-relevant plus --reason).")
    if note is not None:
        out += ["--note", note]
    if cat is not None:
        out += ["--category", cat]
    return out


def build_parser():
    ap = argparse.ArgumentParser(description="Set or add a seen-jobs.csv row (validated by the vocabulary).")
    ap.add_argument("job_id")
    ap.add_argument("--status"); ap.add_argument("--reason"); ap.add_argument("--blocker")
    ap.add_argument("--app-id", dest="app_id"); ap.add_argument("--note"); ap.add_argument("--category")
    ap.add_argument("--workplace"); ap.add_argument("--source")
    ap.add_argument("--add", action="store_true", help="create the row when the id is not present")
    ap.add_argument("--company"); ap.add_argument("--title"); ap.add_argument("--location")
    return ap


def main(argv):
    vocab = load_vocab()
    mapped = legacy_to_args(argv, vocab)
    args = build_parser().parse_args(mapped if mapped is not None else argv)
    if not any([args.status, args.reason, args.blocker is not None, args.app_id, args.note is not None,
                args.category, args.workplace, args.source, args.add]):
        die("nothing to change; give --status, --reason, --blocker, --app-id, --note, --category, --workplace, --source or --add")
    rows = read_ledger(vocab)
    add = None
    if args.add:
        add = {"company": args.company, "title": args.title, "location": args.location}
        if args.status is None:
            args.status = "New"
    if args.app_id:
        d = load_apps() if os.path.exists(path("data/applications.json")) else {"apps": []}
        if not any(a.get("id") == args.app_id for a in d["apps"]):
            die(f"{args.app_id} is not in data/applications.json")
    row, created = apply_update(vocab, rows, args.job_id, add=add, status=args.status, reason=args.reason,
                                blocker=args.blocker, app_id=args.app_id, note=args.note, category=args.category,
                                workplace=args.workplace, source=args.source)
    save_ledger(rows, vocab)
    if row["app_id"] and args.blocker is not None:
        sync_app_blocker(row["app_id"], args.blocker)
    print(("added " if created else "updated ") + f"{args.job_id}: status={row['status']} reason={row['reason']} "
          f"blocker={row['blocker']} app_id={row['app_id']}")


if __name__ == "__main__":
    main(sys.argv[1:])
