#!/usr/bin/env python3
"""Is the active tenant fully set up? Run at the end of setup and whenever something feels off. Stdlib only.

Prints one line per finding: ERROR (blocks the first real run), WARN (works, but ask the person soon) or ok.
Exit 1 when there is any ERROR. It checks the things setup is responsible for: identity, the rules in
REQUIREMENTS.md filled in (no empty sections, approval and follow-up choices recorded), facts, resume built,
search queue seeded, company boards, follow-up consent matching the scheduled task setting, then runs the
consistency and leak checks.
"""
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tenant

ROOT = tenant.root()
OUT = []


def add(level, msg):
    OUT.append((level, msg))
    print(f"{level:5} {msg}")


def read(rel):
    try:
        with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
            return f.read()
    except OSError:
        return None


def sections(text):
    parts = re.split(r"(?m)^## ", text)
    return {p.split("\n", 1)[0].strip(): (p.split("\n", 1)[1] if "\n" in p else "") for p in parts[1:]}


def empty_section(body):
    """True when the section still has an unanswered prompt ('- Label:' with nothing after it, a bare '- ', or an empty pay row)."""
    for l in body.split("\n"):
        s = l.strip()
        if s == "-" or re.fullmatch(r"-\s+[^:]{1,80}:", s):
            return True
        if re.fullmatch(r"\|\s*\(market\).*\|", s):
            return True
    return not any(l.strip() for l in body.split("\n"))


def main():
    meta = tenant.tenant_meta(ROOT)
    for k in ("name", "email", "phone"):
        add("ok" if meta.get(k) else "ERROR", f"tenant.json {k}" + ("" if meta.get(k) else " is empty (needed by the leak checker and the resume)"))

    req = read("REQUIREMENTS.md")
    if req is None:
        add("ERROR", "REQUIREMENTS.md is missing")
    else:
        secs = sections(req)
        for name in ("Role", "Seniority", "Pay", "Location", "Office days", "Company"):
            body = secs.get(name)
            if body is None:
                add("ERROR", f"REQUIREMENTS.md has no '{name}' section")
            elif empty_section(body):
                add("ERROR", f"REQUIREMENTS.md section '{name}' is still empty: ask the person")
            else:
                add("ok", f"REQUIREMENTS.md {name}")
        if "(not set)" in req:
            add("ERROR", "REQUIREMENTS.md still has '(not set)': record the submit-approval and follow-up consent choices")
        else:
            add("ok", "approval and follow-up choices recorded")

    fu = meta.get("followup", {})
    if fu.get("enabled") and not fu.get("task_id"):
        add("WARN", "follow-up consent is yes but no scheduled task id is recorded in tenant.json (create the weekday task)")
    elif fu.get("enabled"):
        add("ok", f"follow-up scheduled task recorded ({fu['task_id']}), channels: {', '.join(fu.get('channels', [])) or 'none'}")
    else:
        add("ok", "follow-up: on request only")

    prof = read("candidate-profile.md") or ""
    n = len(re.findall(r"CONFIRM", prof))
    add("WARN" if n else "ok", f"candidate-profile.md has {n} CONFIRM item(s) still open" if n else "candidate-profile.md has no open CONFIRM items")
    if len(prof) < 800 or "Title, Employer" in prof:
        add("ERROR", "candidate-profile.md looks like the empty template")

    det = read("applicant-details.md") or ""
    if not re.search(r"(?m)^\| Email \| \S", det) or not re.search(r"(?m)^\| Phone \| \S", det):
        add("ERROR", "applicant-details.md has no email or phone in the Personal table")
    else:
        add("ok", "applicant-details.md contact fields")

    try:
        rc = json.loads(read("resume-content.json") or "{}")
        base = rc.get("configs", {}).get("base", {})
        if not (rc.get("experience") and base.get("summary") and base.get("headline")):
            add("ERROR", "resume-content.json has no experience or base headline/summary")
        else:
            add("ok", "resume-content.json")
    except ValueError:
        add("ERROR", "resume-content.json is not valid JSON")
    add("ok" if os.path.exists(os.path.join(ROOT, "resume.pdf")) else "ERROR",
        "resume.pdf built" if os.path.exists(os.path.join(ROOT, "resume.pdf")) else "resume.pdf missing: run tools/make_resumes.py")

    try:
        q = json.loads(read("data/search-queue.json") or "{}").get("queue", [])
    except ValueError:
        q = []
    add("ok" if q else "ERROR", f"search queue has {len(q)} entries" if q else "search queue is empty: run tools/seed_queue.py")
    try:
        b = json.loads(read("data/boards.json") or "{}")
        add("ok" if b.get("boards") else "WARN", "company boards listed" if b.get("boards") else "data/boards.json has no boards (company-board search skipped)")
    except ValueError:
        add("ERROR", "data/boards.json is not valid JSON")

    here = os.path.dirname(os.path.abspath(__file__))
    env = {**os.environ, "JOBS_ROOT": ROOT}
    for tool in ("check_consistency.py", "check_leaks.py"):
        p = subprocess.run([sys.executable, os.path.join(here, tool)], capture_output=True, text=True, env=env)
        add("ok" if p.returncode == 0 else "ERROR", tool if p.returncode == 0 else f"{tool} failed: " + " | ".join(l for l in p.stdout.splitlines() if l.startswith(("ERROR", "LEAK")))[:300])

    errs = sum(1 for l, _ in OUT if l == "ERROR")
    warns = sum(1 for l, _ in OUT if l == "WARN")
    print(f"--- {errs} error(s), {warns} warning(s). " + ("READY" if not errs else "NOT READY"))
    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()
