#!/usr/bin/env python3
"""Tenant resolver. Every tool gets its data root from here, so one person's files can never be read or written
through another person's run.

A tenant is a folder tenants/<id>/ holding one person's profile, rules, ledger, applications and board.
The engine (tools, skills, config, templates) is shared and holds no personal data.

Resolution order for the tenant root:
  1. env JOBS_ROOT   an explicit folder (tests and special cases)
  2. env JOBS_TENANT a tenant id
  3. tenants/.active the id written by `tenant.py use` / `tenant.py create`

CLI (run from the repo root):
  python3 tools/tenant.py show            print the active tenant, its root and whether its files exist
  python3 tools/tenant.py list            list tenants
  python3 tools/tenant.py use <id>        make a tenant active
  python3 tools/tenant.py create "Full Name" [--id slug]   copy tenants/_template to tenants/<id>/, make it active
  python3 tools/tenant.py path            print the active root only
"""
import json
import os
import re
import shutil
import sys

ENGINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TENANTS = os.path.join(ENGINE, "tenants")
TEMPLATE = os.path.join(TENANTS, "_template")
ACTIVE = os.path.join(TENANTS, ".active")
REQUIRED = ("data/applications.json", "data/seen-jobs.csv", "tenant.json")


def die(msg):
    sys.exit("error: " + msg)


def slugify(name):
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s or "tenant"


def tenant_ids():
    if not os.path.isdir(TENANTS):
        return []
    return sorted(d for d in os.listdir(TENANTS)
                  if not d.startswith((".", "_")) and os.path.isdir(os.path.join(TENANTS, d)))


def active_id():
    try:
        with open(ACTIVE, encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


def root():
    """The tenant root for this run. Exits with a plain message when there is none."""
    explicit = (os.environ.get("JOBS_ROOT") or "").strip()
    if explicit:
        r = os.path.realpath(explicit)
        if r == os.path.realpath(ENGINE):
            die("JOBS_ROOT points at the engine folder; it must be a tenant folder.")
        return r
    tid = (os.environ.get("JOBS_TENANT") or "").strip() or active_id()
    if not tid:
        die("no tenant yet. Run the setup skill (python3 tools/tenant.py create \"Full Name\").")
    if tid in ("_template",) or "/" in tid or tid.startswith("."):
        die(f"invalid tenant id '{tid}'")
    r = os.path.join(TENANTS, tid)
    if not os.path.isdir(r):
        die(f"tenant '{tid}' does not exist in tenants/. Known: {', '.join(tenant_ids()) or 'none'}")
    return os.path.realpath(r)


def engine_path(*parts):
    return os.path.join(ENGINE, *parts)


def inside(p, base=None):
    """True when path p is inside the tenant root (or base)."""
    base = os.path.realpath(base or root())
    rp = os.path.realpath(p)
    return rp == base or rp.startswith(base + os.sep)


def load_vocab(tenant_root=None):
    """Engine vocabulary merged with the tenant's data/vocab.overrides.json (tenant keys replace engine keys)."""
    with open(engine_path("config", "vocab.json"), encoding="utf-8") as f:
        v = json.load(f)
    p = os.path.join(tenant_root or root(), "data", "vocab.overrides.json")
    if os.path.isfile(p):
        with open(p, encoding="utf-8") as f:
            v.update(json.load(f))
    return v


def tenant_meta(tenant_root=None):
    p = os.path.join(tenant_root or root(), "tenant.json")
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def create(name, tid=None):
    name = " ".join(name.split())
    if not name:
        die("a name is required")
    tid = slugify(tid or name)
    if tid.startswith("_"):
        die("tenant ids cannot start with an underscore")
    base, n = tid, 2
    while os.path.exists(os.path.join(TENANTS, tid)):
        tid = f"{base}-{n}"
        n += 1
    if not os.path.isdir(TEMPLATE):
        die("tenants/_template is missing; the engine is incomplete. Pull the latest engine.")
    dest = os.path.join(TENANTS, tid)
    shutil.copytree(TEMPLATE, dest)
    for dirpath, _, files in os.walk(dest):
        for fn in files:
            p = os.path.join(dirpath, fn)
            try:
                with open(p, encoding="utf-8") as f:
                    t = f.read()
            except (UnicodeDecodeError, OSError):
                continue
            t2 = t.replace("{{NAME}}", name).replace("{{ID}}", tid).replace("{{NAME_UNDERSCORE}}", name.replace(" ", "_"))
            if t2 != t:
                with open(p, "w", encoding="utf-8", newline="\n") as f:
                    f.write(t2)
    use(tid)
    return tid, dest


def use(tid):
    if tid not in tenant_ids():
        die(f"unknown tenant '{tid}'. Known: {', '.join(tenant_ids()) or 'none'}")
    os.makedirs(TENANTS, exist_ok=True)
    with open(ACTIVE, "w", encoding="utf-8", newline="\n") as f:
        f.write(tid + "\n")


def main(argv):
    cmd = argv[0] if argv else "show"
    if cmd == "path":
        print(root())
    elif cmd == "list":
        act = active_id()
        for t in tenant_ids():
            print(("* " if t == act else "  ") + t)
        if not tenant_ids():
            print("(none)")
    elif cmd == "use":
        if len(argv) < 2:
            die("usage: tenant.py use <id>")
        use(argv[1])
        print("active tenant:", argv[1])
    elif cmd == "create":
        if len(argv) < 2:
            die('usage: tenant.py create "Full Name" [--id slug]')
        tid = argv[argv.index("--id") + 1] if "--id" in argv else None
        tid, dest = create(argv[1], tid)
        print(f"created tenant '{tid}' at {dest} and made it active")
    elif cmd == "show":
        r = root()
        meta = tenant_meta(r)
        print("tenant:", meta.get("id") or os.path.basename(r))
        print("name:  ", meta.get("name", "(unset)"))
        print("root:  ", r)
        missing = [x for x in REQUIRED if not os.path.exists(os.path.join(r, x))]
        print("files: ", "ok" if not missing else "missing " + ", ".join(missing))
    else:
        die("commands: show, list, use, create, path")


if __name__ == "__main__":
    main(sys.argv[1:])
