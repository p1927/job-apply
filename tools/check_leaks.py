#!/usr/bin/env python3
"""Find personal data where it must not be. Stdlib only.

Identifiers (full name, email, phone digits) come from each tenant's tenant.json.
Rules:
  1. No engine file (anything outside tenants/) may contain any tenant's identifiers.
  2. No tenant's files may contain another tenant's identifiers.
A tenant's own files may of course contain its own.
Usage: python3 tools/check_leaks.py        exit 1 and one line per finding when something leaks
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tenant

ALLOWED_ENGINE_FILES = {"LICENSE"}   # copyright line names the maintainer on purpose
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "tenants"}
TEXT_EXT = {".md", ".py", ".sh", ".json", ".csv", ".txt", ".yml", ".yaml", ".html", ".mjs", ".js", ".toml", ""}


def identifiers(tid):
    try:
        with open(os.path.join(tenant.TENANTS, tid, "tenant.json"), encoding="utf-8") as f:
            m = json.load(f)
    except (OSError, ValueError):
        return []
    out = []
    for k in ("name", "email", "phone"):
        v = (m.get(k) or "").strip()
        if not v:
            continue
        if k == "phone":
            d = re.sub(r"\D", "", v)
            if len(d) >= 7:
                out.append(("phone", d))
        elif k == "name":
            if len(v) >= 5 and " " in v:
                out.append(("name", v.lower()))
        else:
            out.append((k, v.lower()))
    return out


def files(base, skip_top=()):
    for dirpath, dirs, fns in os.walk(base):
        rel = os.path.relpath(dirpath, base)
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not (rel == "." and d in skip_top)]
        for fn in fns:
            if os.path.splitext(fn)[1].lower() in TEXT_EXT:
                yield os.path.join(dirpath, fn)


def hits(path, ids):
    try:
        with open(path, encoding="utf-8") as f:
            t = f.read()
    except (OSError, UnicodeDecodeError):
        return []
    low, digits = t.lower(), re.sub(r"\D", "", t)
    found = []
    for kind, val in ids:
        if (kind == "phone" and val in digits) or (kind != "phone" and val in low):
            found.append(kind)
    return found


def scan():
    problems = []
    ids = {t: identifiers(t) for t in tenant.tenant_ids()}
    allids = [x for v in ids.values() for x in v]
    for p in files(tenant.ENGINE):
        if os.path.relpath(p, tenant.ENGINE) in ALLOWED_ENGINE_FILES:
            continue
        for kind in hits(p, allids):
            problems.append(f"engine file {os.path.relpath(p, tenant.ENGINE)} contains a tenant {kind}")
    for t, mine in ids.items():
        others = [x for u, v in ids.items() if u != t for x in v if x not in mine]   # two people with one name share it; only differing identifiers count
        if not others:
            continue
        base = os.path.join(tenant.TENANTS, t)
        for p in files(base):
            for kind in hits(p, others):
                problems.append(f"tenant {t}: {os.path.relpath(p, base)} contains another tenant's {kind}")
    return problems


if __name__ == "__main__":
    pr = scan()
    for line in pr:
        print("LEAK", line)
    print(f"--- {len(pr)} leak(s)")
    sys.exit(1 if pr else 0)
