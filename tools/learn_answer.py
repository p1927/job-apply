#!/usr/bin/env python3
"""Save a newly learned form answer, fact or ATS quirk.

Usage: learn_answer.py "question pattern" "answer" [--where TEXT] [--date YYYY-MM-DD]
                       [--kind answer|fact|quirk] [--dry-run]
answer/fact: upsert a row in the 'Learned answers' table of applicant-details.md.
quirk: append 'system | behaviour | what works | date' under 'Add what you learn here'
       in .claude/skills/job-search/ats-playbook.md (pattern = system, answer = "behaviour => what works"
       or just behaviour; --where may carry what works).
Works on the active tenant (tools/tenant.py). Never commits.
"""
import argparse, datetime as dt, os, re, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tenant

ROOT = tenant.root()
ENGINE = tenant.ENGINE
LA_HEAD = "| Question pattern | Answer | Learned (date) | Where seen |\n| --- | --- | --- | --- |"
Q_HEAD = "| System | Behaviour | What works | Date |\n| --- | --- | --- | --- |"


def atomic_write(path, text):
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".tmp-")
    with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    os.replace(tmp, path)


def cell(s):
    return re.sub(r"\s+", " ", (s or "").replace("|", "/")).strip()


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def upsert(text, heading, head_block, row, key_idx, key):
    """Insert or replace a table row in the section with this heading. Returns (text, action)."""
    m = re.search(rf"^## {re.escape(heading)}[ \t]*$", text, re.M)
    line = "| " + " | ".join(row) + " |"
    if not m:
        return text.rstrip("\n") + f"\n\n## {heading}\n{head_block}\n{line}\n", "added (new section)"
    nxt = re.search(r"^## ", text[m.end():], re.M)
    end = m.end() + nxt.start() if nxt else len(text)
    lines = text[m.end():end].rstrip("\n").split("\n")
    if not any(l.startswith("| ---") for l in lines):
        lines = lines + [""] + head_block.split("\n")
    action = None
    for i, l in enumerate(lines):
        if l.startswith("|") and not l.startswith("| ---"):
            cells = [c.strip() for c in l.strip().strip("|").split("|")]
            if len(cells) > key_idx and norm(cells[key_idx]) == key and not l.startswith("| Question") \
                    and not l.startswith("| System"):
                lines[i], action = line, "updated existing row"
                break
    if action is None:
        last = max(i for i, l in enumerate(lines) if l.startswith("|"))
        lines.insert(last + 1, line)
        action = "added"
    new = "\n".join(lines) + "\n" + ("\n" if nxt else "")
    return text[:m.end()] + new + text[end:], action


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pattern"); ap.add_argument("answer")
    ap.add_argument("--where", default=""); ap.add_argument("--date")
    ap.add_argument("--kind", choices=["answer", "fact", "quirk"], default="answer")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if not a.answer.strip():
        sys.exit("error: empty answer refused")
    if not norm(a.pattern):
        sys.exit("error: empty question pattern refused")
    date = a.date or dt.date.today().isoformat()
    try:
        dt.date.fromisoformat(date)
    except ValueError:
        sys.exit("error: bad --date, use YYYY-MM-DD")

    if a.kind == "quirk":
        # the shared playbook is edited only on the maintainer's machine; elsewhere quirks stay in this tenant's own file
        path = (os.path.join(ENGINE, ".claude/skills/job-search/ats-playbook.md") if os.path.exists(os.path.join(ENGINE, ".engine-maintainer"))
                else os.path.join(ROOT, "ats-quirks.md"))
        behaviour, _, works = a.answer.partition("=>")
        works = works.strip() or a.where
        row = [cell(a.pattern), cell(behaviour), cell(works), date]
        heading, head, idx, key = "Add what you learn here", Q_HEAD, 0, norm(a.pattern + " " + behaviour)
        # key on system + behaviour: compare both columns by joining
        text = open(path, encoding="utf-8").read() if os.path.isfile(path) else "# ATS playbook\n"
        text, action = upsert_quirk(text, heading, head, row)
    else:
        path = os.path.join(ROOT, "applicant-details.md")
        if not os.path.isfile(path):
            sys.exit(f"error: missing {path}")
        row = [cell(a.pattern), cell(a.answer), date, cell(a.where)]
        text = open(path, encoding="utf-8").read()
        text, action = upsert(text, "Learned answers", LA_HEAD, row, 0, norm(a.pattern))

    rel = os.path.relpath(path, ENGINE if a.kind == "quirk" else ROOT)
    print(f"{action}: {rel}\n| " + " | ".join(row) + " |")
    if a.dry_run:
        print("DRY RUN, nothing written.")
        return
    atomic_write(path, text)
    print("git add " + rel)


def upsert_quirk(text, heading, head, row):
    """Quirk rows are keyed on system + behaviour."""
    key = norm(row[0] + " " + row[1])
    m = re.search(rf"^## {re.escape(heading)}[ \t]*$", text, re.M)
    line = "| " + " | ".join(row) + " |"
    if not m:
        return text.rstrip("\n") + f"\n\n## {heading}\n{head}\n{line}\n", "added (new section)"
    nxt = re.search(r"^## ", text[m.end():], re.M)
    end = m.end() + nxt.start() if nxt else len(text)
    lines = text[m.end():end].rstrip("\n").split("\n")
    if not any(l.startswith("| ---") for l in lines):
        lines += [""] + head.split("\n")
    action = None
    for i, l in enumerate(lines):
        if l.startswith("|") and not l.startswith("| ---") and not l.startswith("| System"):
            c = [x.strip() for x in l.strip().strip("|").split("|")]
            if len(c) >= 2 and norm(c[0] + " " + c[1]) == key:
                lines[i], action = line, "updated existing row"
                break
    if action is None:
        last = max(i for i, l in enumerate(lines) if l.startswith("|"))
        lines.insert(last + 1, line)
        action = "added"
    return text[:m.end()] + "\n".join(lines) + "\n" + ("\n" if nxt else "") + text[end:], action


if __name__ == "__main__":
    main()
