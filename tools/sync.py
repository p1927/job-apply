#!/usr/bin/env python3
"""One command to save everything: commit and push the engine repo and the active tenant's repo, each only if it
has changes. Tenant data and engine code are separate git repos; this keeps them in step so nobody tracks two.

Usage: python3 tools/sync.py [--no-push] [--pull] [--status] [-m "message"]
- engine: this repo. Maintainer machines (file .engine-maintainer present) commit and push it; every other machine
  only merges engine updates. tenants/ is gitignored, so tenant data never enters the engine.
- tenant: tenants/<id>/ when it is its own git repo. A tenant without a repo (no backup set up) is skipped with a note.
- --status: print what would be saved (changed files, unpushed commits) and change nothing.
Merge only: it never rebases, never autostashes, never force-pushes. Only intended files are staged: other agents' temp files
(.tmp-*, *.part, *.tmp) and the data lock file are never committed. A failed merge or push keeps the local commit; Claude retries.
"""
import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tenant

COAUTHOR = "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
# Never staged, whatever the repo's own .gitignore says (pathspec magic, so no ignore file is needed in old tenants).
EXCLUDES = [":(exclude,glob)**/.tmp-*", ":(exclude,glob)**/*.part", ":(exclude,glob)**/*.tmp", ":(exclude)data/.lock", ":(exclude).claude/worktrees",
            ":(exclude,glob)**/.lock"]


def git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)


def is_repo_root(path):
    p = git(path, "rev-parse", "--show-toplevel")
    return p.returncode == 0 and os.path.realpath(p.stdout.strip()) == os.path.realpath(path)


def merge_upstream(path):
    """Merge only: fetch, then merge the upstream branch. Returns (ok, message)."""
    f = git(path, "fetch", "-q")
    if f.returncode != 0:
        return False, f"could not reach the remote ({f.stderr.strip()[:150]})"
    if git(path, "rev-parse", "--abbrev-ref", "@{u}").returncode != 0:
        return True, "no upstream yet"
    m = git(path, "merge", "--no-edit", "-q", "@{u}")
    if m.returncode != 0:
        git(path, "merge", "--abort")
        return False, f"merge needs attention ({(m.stderr.strip() or m.stdout.strip())[:150]}); nothing was changed"
    return True, "merged"


def changed_files(path):
    return [ln for ln in git(path, "status", "--porcelain", "--", ".", *EXCLUDES).stdout.splitlines() if ln.strip()]


def status(label, path):
    if not os.path.isdir(path) or not is_repo_root(path):
        return f"{label}: no git repo here, skipped"
    n = len(changed_files(path))
    up = git(path, "rev-list", "--count", "@{u}..HEAD")
    unpushed = up.stdout.strip() if up.returncode == 0 else "unknown (no upstream)"
    return f"{label}: {n} files changed, {unpushed} unpushed commits"


def sync(label, path, msg, push):
    if not os.path.isdir(path) or not is_repo_root(path):
        return f"{label}: no git repo here, skipped"
    out = []
    branch = git(path, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    if branch in ("HEAD", ""):
        return f"{label}: detached HEAD, nothing committed or pushed. Claude: run git -C {path} switch main, then sync again"
    if changed_files(path):
        meta = tenant.tenant_meta(path) if label == "data" else {}
        ident = []
        if meta.get("git_name") and meta.get("git_email"):
            ident = ["-c", f"user.name={meta['git_name']}", "-c", f"user.email={meta['git_email']}"]
        git(path, "add", "-A", "--", ".", *EXCLUDES)
        if git(path, "diff", "--cached", "--quiet").returncode != 0:
            c = git(path, *ident, "commit", "-q", "-m", f"{msg}\n\n{COAUTHOR}")
            if c.returncode != 0:
                return f"{label}: COMMIT FAILED: {c.stderr.strip() or c.stdout.strip()}"
            out.append("committed")
    if not push:
        return f"{label}: {', '.join(out) or 'nothing to commit'}, not pushed"
    if git(path, "remote").stdout.strip() == "":
        return f"{label}: {', '.join(out) or 'clean'}, no remote configured"
    url = git(path, "remote", "get-url", "origin").stdout.strip()
    repo = url.rsplit("/", 1)[-1].removesuffix(".git") or label
    label = f"{label} (repo {repo})"
    if branch == "gitbutler/workspace":
        return f"{label}: {', '.join(out) or 'clean'}; GitButler workspace here, so run `but push` instead of git push (remote {url})"
    ok, note = merge_upstream(path)
    if not ok:
        return f"{label}: {', '.join(out) or 'clean'} locally, not pushed: {note}. Claude will retry; nothing is lost"
    ahead = git(path, "rev-list", "--count", "@{u}..HEAD")
    if ahead.returncode == 0 and ahead.stdout.strip() == "0":
        return f"{label}: {', '.join(out) or 'already up to date'}"
    ps = git(path, "push", "-q", "-u", "origin", branch)
    if ps.returncode != 0:
        return f"{label}: {', '.join(out) or 'clean'} locally, push failed ({ps.stderr.strip()[:200]}). Claude will retry; nothing is lost"
    return f"{label}: {', '.join(out) or 'nothing new'}, pushed"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-push", action="store_true")
    ap.add_argument("--pull", action="store_true", help="only merge: update the engine and the tenant repo, commit nothing")
    ap.add_argument("--status", action="store_true", help="show what would be saved; change nothing")
    ap.add_argument("-m", default="Update job-search data")
    a = ap.parse_args()
    push = not a.no_push
    try:
        troot = tenant.root()
    except SystemExit:
        troot = None
    if a.status:
        print(status("engine", tenant.ENGINE))
        if troot:
            print(status("data", troot))
        return
    if a.pull:
        ok, note = merge_upstream(tenant.ENGINE)
        print("engine: " + ("up to date" if ok else "continuing with the version you have (" + note + ")"))
        if troot and is_repo_root(troot) and git(troot, "remote").stdout.strip():
            ok, note = merge_upstream(troot)
            print("data: " + ("up to date" if ok else "not updated (" + note + "); Claude will retry"))
        else:
            print("data: no remote, nothing to pull")
        return
    if os.path.exists(os.path.join(tenant.ENGINE, ".engine-maintainer")):
        print(sync("engine", tenant.ENGINE, "Update engine" if a.m == "Update job-search data" else a.m, push))
    elif push:
        ok, note = merge_upstream(tenant.ENGINE)
        print("engine: updated from upstream" if ok else "engine: continuing with the version you have (" + note + ")")
    if troot:
        print(sync("data", troot, a.m, push))


if __name__ == "__main__":
    main()
