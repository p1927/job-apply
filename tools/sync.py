#!/usr/bin/env python3
"""One command to save everything: commit and push the engine repo and the active tenant's repo, each only if it
has changes. Tenant data and engine code are separate git repos; this keeps them in step so nobody tracks two.

Usage: python3 tools/sync.py [--no-push] [--pull] [-m "message"]
- engine: this repo. Maintainer machines (file .engine-maintainer present) commit and push it; every other machine
  only pulls engine updates (rebase, keeping any local quirk notes). tenants/ is gitignored, so tenant data never enters the engine.
- tenant: tenants/<id>/ when it is its own git repo. A tenant without a repo (no backup set up) is skipped with a note.
Never force-pushes. A failed pull or push is reported with the exact recovery step, and the local commit is kept.
"""
import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tenant

COAUTHOR = "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"


def git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)


def is_repo_root(path):
    p = git(path, "rev-parse", "--show-toplevel")
    return p.returncode == 0 and os.path.realpath(p.stdout.strip()) == os.path.realpath(path)


def sync(label, path, msg, push):
    if not os.path.isdir(path) or not is_repo_root(path):
        return f"{label}: no git repo here, skipped"
    out = []
    if git(path, "status", "--porcelain").stdout.strip():
        meta = tenant.tenant_meta(path) if label == "data" else {}
        ident = []
        if meta.get("git_name") and meta.get("git_email"):
            ident = ["-c", f"user.name={meta['git_name']}", "-c", f"user.email={meta['git_email']}"]
        git(path, "add", "-A")
        c = git(path, *ident, "commit", "-q", "-m", f"{msg}\n\n{COAUTHOR}")
        if c.returncode != 0:
            return f"{label}: COMMIT FAILED: {c.stderr.strip() or c.stdout.strip()}"
        out.append("committed")
    if not push:
        return f"{label}: {', '.join(out) or 'nothing to commit'}, not pushed"
    if git(path, "remote").stdout.strip() == "":
        return f"{label}: {', '.join(out) or 'clean'}, no remote configured"
    branch = git(path, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    pull = git(path, "pull", "--rebase", "--autostash", "-q")
    if pull.returncode != 0:
        git(path, "rebase", "--abort")
        return f"{label}: {', '.join(out)} locally, PULL FAILED ({pull.stderr.strip()[:200]}). Fix, then: git -C {path} pull --rebase && git -C {path} push"
    ahead = git(path, "rev-list", "--count", "@{u}..HEAD")
    if ahead.returncode == 0 and ahead.stdout.strip() == "0":
        return f"{label}: {', '.join(out) or 'already up to date'}"
    ps = git(path, "push", "-q", "origin", branch)
    if ps.returncode != 0:
        return f"{label}: {', '.join(out)} locally, PUSH FAILED ({ps.stderr.strip()[:200]}). Fix, then: git -C {path} push origin {branch}"
    return f"{label}: {', '.join(out) or 'nothing new'}, pushed"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-push", action="store_true")
    ap.add_argument("--pull", action="store_true", help="only pull: update the engine and the tenant repo, commit nothing")
    ap.add_argument("-m", default="Update job-search data")
    a = ap.parse_args()
    push = not a.no_push
    if a.pull:
        p = git(tenant.ENGINE, "pull", "--rebase", "--autostash", "-q")
        print("engine: " + ("up to date" if p.returncode == 0 else "could not update (" + p.stderr.strip()[:150] + ")"))
        try:
            troot = tenant.root()
        except SystemExit:
            return
        if is_repo_root(troot) and git(troot, "remote").stdout.strip():
            q = git(troot, "pull", "--rebase", "--autostash", "-q")
            print("data: " + ("up to date" if q.returncode == 0 else "PULL FAILED (" + q.stderr.strip()[:150] + ")"))
        else:
            print("data: no remote, nothing to pull")
        return
    if os.path.exists(os.path.join(tenant.ENGINE, ".engine-maintainer")):
        print(sync("engine", tenant.ENGINE, "Update engine" if a.m == "Update job-search data" else a.m, push))
    elif push:
        p = git(tenant.ENGINE, "pull", "--rebase", "--autostash", "-q")
        print("engine: updated from upstream" if p.returncode == 0 else "engine: could not update (" + p.stderr.strip()[:150] + ")")
    try:
        troot = tenant.root()
    except SystemExit:
        return
    print(sync("data", troot, a.m, push))


if __name__ == "__main__":
    main()
