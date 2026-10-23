#!/usr/bin/env python3
"""Log an application event (reply, interview, rejection...) to the company file and data.

Usage: log_outcome.py APP-0NN EVENT [--date YYYY-MM-DD] [--with NAME] [--note TEXT]
       [--source email|linkedin|call|calendar] [--round TEXT] [--topics TEXT] [--next TEXT] [--dry-run]
Events: ack screening interview offer rejected withdrawn no-reply-14d info
Works on the active tenant (tools/tenant.py). Never commits or pushes.
"""
import argparse, csv, datetime as dt, io, json, os, re, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tenant

ROOT = tenant.root()
EVENTS = ["ack", "screening", "interview", "offer", "rejected", "withdrawn", "no-reply-14d", "info"]
STATUS_EVENTS = {"screening": "Screening", "interview": "Interview", "offer": "Offer",
                 "rejected": "Rejected", "withdrawn": "Withdrawn"}
TERMINAL = {"Rejected", "Withdrawn", "Dropped"}
LOG_HEAD = ("| Date | Round | With | Topics asked | What we said | Next step |\n"
            "| --- | --- | --- | --- | --- | --- |")


def die(msg):
    sys.exit("error: " + msg)


def atomic_write(path, text):
    d = os.path.dirname(path)
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".tmp-")
    with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    os.replace(tmp, path)


def cell(s):
    return (s or "").replace("|", "/").replace("\n", " ").strip()


def add_log_row(text, row):
    line = "| " + " | ".join(cell(c) for c in row) + " |"
    m = re.search(r"^## Interview log[ \t]*$", text, re.M)
    if not m:
        return text.rstrip("\n") + "\n\n## Interview log\n" + LOG_HEAD + "\n" + line + "\n"
    nxt = re.search(r"^## ", text[m.end():], re.M)
    end = m.end() + nxt.start() if nxt else len(text)
    sec = text[m.end():end]
    if "| --- |" not in sec:
        sec = "\n" + LOG_HEAD + "\n" + sec.lstrip("\n")
    lines = sec.rstrip("\n").split("\n")
    last = max(i for i, l in enumerate(lines) if l.startswith("|"))
    lines.insert(last + 1, line)
    new = "\n".join(lines) + "\n" + ("\n" if nxt else "")
    return text[:m.end()] + new + text[end:]


def fill_outcome(text, status, date, reason):
    fields = [("Outcome status", status), ("Date", date), ("Reason", reason or "(not given)"),
              ("What to improve", "(to fill: what would change the next application?)")]
    body = "\n".join(f"- {k}: {v}" for k, v in fields) + "\n"
    m = re.search(r"^## Outcome[ \t]*$", text, re.M)
    if not m:
        return text.rstrip("\n") + "\n\n## Outcome\n" + body
    nxt = re.search(r"^## ", text[m.end():], re.M)
    end = m.end() + nxt.start() if nxt else len(text)
    return text[:m.end()] + "\n" + body + ("\n" if nxt else "") + text[end:]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("app"); ap.add_argument("event")
    ap.add_argument("--date"); ap.add_argument("--with", dest="with_", default="")
    ap.add_argument("--note", default=""); ap.add_argument("--round", default="")
    ap.add_argument("--source", choices=["email", "linkedin", "call", "calendar"])
    ap.add_argument("--topics", default=""); ap.add_argument("--next", dest="next_", default="")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    if a.event not in EVENTS:
        die(f"unknown event {a.event!r}; use one of {', '.join(EVENTS)}")
    date = a.date or dt.date.today().isoformat()
    try:
        d0 = dt.date.fromisoformat(date)
    except ValueError:
        die("bad --date, use YYYY-MM-DD")

    vocab = tenant.load_vocab(ROOT)
    jpath = os.path.join(ROOT, "data/applications.json")
    data = json.load(open(jpath, encoding="utf-8"))
    app = next((x for x in data["apps"] if x.get("id") == a.app), None)
    if not app:
        die(f"unknown app id {a.app}")
    cpath = os.path.join(ROOT, app.get("detail") or f"applications/{a.app}.md")
    if not os.path.isfile(cpath):
        die(f"company file missing: {cpath}")

    writes = {}
    text = open(cpath, encoding="utf-8").read()
    note = a.note
    if a.source:
        note = (note + f" (via {a.source})").strip()
    if a.event == "ack" and not a.round:
        a.round = "Application received"
    elif a.event == "no-reply-14d" and not a.round:
        a.round = "No reply after 14 days"
    text = add_log_row(text, [date, a.round or a.event, a.with_, a.topics, note, a.next_])

    new_status = STATUS_EVENTS.get(a.event)
    if new_status:
        if new_status not in vocab["app_status"]:
            die(f"status {new_status} not in vocab app_status")
        app["status"] = new_status
        text = re.sub(r"^- Status:.*$", f"- Status: {new_status}", text, count=1, flags=re.M)
    if a.event == "rejected":
        text = fill_outcome(text, "Rejected", date, a.note)
    writes[cpath] = text

    fu = app.setdefault("followUp", {})
    fu["lastCheck"] = date
    final = app.get("status") in TERMINAL
    fu["nextCheck"] = None if final else (d0 + dt.timedelta(days=7)).isoformat()
    jtext = json.dumps(data, indent=1, ensure_ascii=False) + "\n"
    writes[jpath] = jtext

    # Ledger status stays Applied; append a short note to the CSV row.
    cpath_csv = os.path.join(ROOT, "data/seen-jobs.csv")
    if os.path.isfile(cpath_csv):
        raw = open(cpath_csv, encoding="utf-8", newline="").read()
        rd = csv.DictReader(io.StringIO(raw))
        rows, hdr, hit = list(rd), rd.fieldnames, False
        if hdr and "app_id" in hdr and "note" in hdr:
            for r in rows:
                if r.get("app_id") == a.app:
                    r["note"] = ((r.get("note") or "") + f" [{date} {a.event}]").strip()
                    hit = True
            if hit:
                out = io.StringIO(newline="")
                w = csv.DictWriter(out, fieldnames=hdr, lineterminator="\n")
                w.writeheader(); w.writerows(rows)
                writes[cpath_csv] = out.getvalue()

    summary = [f"{a.app} {a.event} {date}: " + (f"status -> {app['status']}; " if new_status else "status unchanged; ")
               + f"lastCheck {date}, nextCheck {fu['nextCheck']}"]
    if a.dry_run:
        print("DRY RUN, nothing written.\n" + "\n".join(summary))
        for p in writes:
            print("would write", os.path.relpath(p, ROOT))
        return
    for p, t in writes.items():
        atomic_write(p, t)
    print("\n".join(summary))
    rels = [os.path.relpath(p, ROOT) for p in writes]
    print("git add " + " ".join(rels))
    print("now run python3 tools/build_board.py")


if __name__ == "__main__":
    main()
