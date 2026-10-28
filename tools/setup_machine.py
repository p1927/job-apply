#!/usr/bin/env python3
"""Check (and with --fix, install) everything the job-search system needs on this machine. Stdlib only.

Usage: python3 tools/setup_machine.py            report only
       python3 tools/setup_machine.py --fix      install or wire up whatever can be done without a password
Exit code 0 when everything needed is ready, 1 otherwise. Lines starting with NEEDS_HUMAN are the few things only a
person can do (an installer password, a macOS prompt); say them in plain words and run again afterwards.

Checks: git, python 3.9+, Google Chrome (builds the PDF resumes), BrowserOS neo
(the browser agents use) and its MCP server registered in Claude Code. Optional extras: node 22+ with a career-ops
clone next to this repo, and the GitHub CLI (only for an online backup).
"""
import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import urllib.error
import urllib.request

ENGINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAREER_OPS_REPO = os.environ.get("CAREER_OPS_REPO") or "https://github.com/p1927/career-ops.git"   # public fork; override with env
CAREER_OPS_DIR = os.environ.get("CAREER_OPS_DIR") or os.path.join(os.path.dirname(ENGINE), "career-ops")
SYSTEM = platform.system()          # Darwin, Windows, Linux
MCP_NAME = "browseros-neo"
MCP_PORTS = (9200, 9010)            # docs.browseros.com/neo/mcp/manual says 9200; some installs use 9010
FIXES, MISSING, HUMAN, OPTIONAL = [], [], [], []   # OPTIONAL: nice to have (career-ops, node, gh); never blocks READY


def run(cmd, **kw):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=kw.pop("timeout", 600), **kw)
    except (OSError, subprocess.TimeoutExpired) as e:
        return subprocess.CompletedProcess(cmd, 1, "", str(e))


def say(ok, name, detail="", optional=False):
    print(("ok      " if ok else ("optional " if optional else "MISSING ")) + name + (f": {detail}" if detail else ""))
    if not ok:
        (OPTIONAL if optional else MISSING).append(name)


def find_brew():
    return shutil.which("brew") or next((p for p in ("/opt/homebrew/bin/brew", "/usr/local/bin/brew") if os.path.isfile(p)), None)


def version_of(cmd):
    p = run(cmd)
    return (p.stdout or p.stderr).strip().split("\n")[0] if p.returncode == 0 else ""


def browseros_installed():
    if SYSTEM == "Darwin":
        return any(os.path.isdir(os.path.join(b, "BrowserOS neo.app")) for b in ("/Applications", os.path.expanduser("~/Applications")))
    if SYSTEM == "Windows":
        local = os.environ.get("LOCALAPPDATA", "")
        return any(os.path.isdir(os.path.join(b, "BrowserOS neo")) for b in (local, os.environ.get("ProgramFiles", "")))
    return False


def chrome_installed():
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    return bool(os.environ.get("CHROME_PATH")) or any(os.path.isfile(c) for c in (
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "/usr/bin/google-chrome", "/usr/bin/chromium",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe", r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"))


def live_endpoint():
    """The BrowserOS neo MCP URL that answers, or ''."""
    for port in MCP_PORTS:
        url = f"http://127.0.0.1:{port}/mcp"
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json, text/event-stream"})
            urllib.request.urlopen(req, timeout=2)
            return url
        except urllib.error.HTTPError:
            return url                      # any HTTP answer means the server is there
        except Exception:
            continue
    return ""


def mcp_registered():
    p = run(["claude", "mcp", "list"]) if shutil.which("claude") else None
    if p is not None and p.returncode == 0 and MCP_NAME in p.stdout:
        return True
    try:
        with open(os.path.expanduser("~/.claude.json"), encoding="utf-8") as f:
            return MCP_NAME in json.load(f).get("mcpServers", {})
    except (OSError, ValueError):
        return False


def registered_url():
    try:
        with open(os.path.expanduser("~/.claude.json"), encoding="utf-8") as f:
            return json.load(f).get("mcpServers", {}).get(MCP_NAME, {}).get("url", "")
    except (OSError, ValueError):
        return ""


def start_browseros(wait=40):
    """Open BrowserOS neo and wait until its MCP server answers. Returns the live URL or ''."""
    import time
    if SYSTEM == "Darwin":
        run(["open", "-a", "BrowserOS neo"])
    end = time.time() + wait
    while time.time() < end:
        url = live_endpoint()
        if url:
            return url
        time.sleep(2)
    return ""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fix", action="store_true")
    fix = ap.parse_args().fix
    brew = find_brew()
    gh_ok = bool(shutil.which("gh"))

    git_v = version_of(["git", "--version"])
    say(bool(git_v), "git", git_v)
    py_ok = sys.version_info >= (3, 9)
    say(py_ok, "python 3.9+", sys.version.split()[0])
    node_v = version_of(["node", "--version"])
    node_ok = bool(node_v) and int(node_v.lstrip("v").split(".")[0]) >= 22
    say(node_ok, "node 22+ (for career-ops)", node_v, optional=True)
    say(chrome_installed(), "Google Chrome (builds PDF resumes)")
    bo = browseros_installed()
    say(gh_ok, "GitHub CLI (only for optional online backup)", optional=True)
    say(bo, "BrowserOS neo")
    reg = mcp_registered()
    say(reg, f"{MCP_NAME} registered in Claude Code")
    live = live_endpoint() if bo else ""
    if bo and not live and fix:
        live = start_browseros()
    say(bool(live), "BrowserOS neo running and answering MCP", live)
    if live and reg and registered_url() and registered_url() != live:
        if fix and shutil.which("claude"):
            run(["claude", "mcp", "remove", "--scope", "user", MCP_NAME])
            FIXES.append(("MCP link repointed to " + live, run(["claude", "mcp", "add", "--transport", "http", "--scope", "user", MCP_NAME, live])))
        else:
            say(False, f"registered URL {registered_url()} differs from live {live}", "run with --fix")
    co = os.path.isfile(os.path.join(CAREER_OPS_DIR, "package.json"))
    say(co, "career-ops clone", CAREER_OPS_DIR, optional=True)
    co_deps = co and os.path.isdir(os.path.join(CAREER_OPS_DIR, "node_modules"))
    if co:
        say(co_deps, "career-ops dependencies installed", optional=True)

    if fix:
        if SYSTEM == "Darwin" and not brew and (not git_v or not bo):
            p = run(["/bin/bash", "-c", 'NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'], timeout=1800)
            brew = find_brew()
            FIXES.append(("Homebrew", p))
            if not brew:
                HUMAN.append("The Mac needs your login password once to install its software installer. Claude will start it; type your Mac password in the window that appears, then tell Claude it is done.")
        if brew:
            if not git_v:
                FIXES.append(("git", run([brew, "install", "git"])))
            if not node_ok:
                FIXES.append(("node", run([brew, "install", "node"])))
            if not gh_ok:
                FIXES.append(("GitHub CLI", run([brew, "install", "gh"])))
            if not bo and SYSTEM == "Darwin":
                run([brew, "tap", "browseros-ai/tap"])
                FIXES.append(("BrowserOS neo", run([brew, "install", "--cask", "browseros-neo"])))
            if not chrome_installed() and SYSTEM == "Darwin":
                FIXES.append(("Google Chrome", run([brew, "install", "--cask", "google-chrome"])))
        elif SYSTEM == "Windows":
            if not bo:
                HUMAN.append("Download and run the BrowserOS neo installer: https://cdn.browseros.com/download/BrowserOS_neo_installer.exe")
        if git_v and not co:
            FIXES.append(("career-ops clone", run(["git", "clone", "--depth", "1", CAREER_OPS_REPO, CAREER_OPS_DIR])))
        if (os.path.isfile(os.path.join(CAREER_OPS_DIR, "package.json")) and shutil.which("npm")
                and not os.path.isdir(os.path.join(CAREER_OPS_DIR, "node_modules"))):
            FIXES.append(("career-ops dependencies", run(["npm", "install", "--no-audit", "--no-fund"], cwd=CAREER_OPS_DIR, timeout=900)))
        if browseros_installed() and not reg:
            url = live_endpoint()
            if not url:
                HUMAN.append("Open BrowserOS neo once (click it in Applications), finish its first-run screen, then tell Claude. The MCP link needs the app running.")
            elif shutil.which("claude"):
                FIXES.append(("MCP link", run(["claude", "mcp", "add", "--transport", "http", "--scope", "user", MCP_NAME, url])))
        for name, p in FIXES:
            print(("fixed   " if p.returncode == 0 else "FAILED  ") + name + ("" if p.returncode == 0 else ": " + (p.stderr or p.stdout).strip()[-200:]))
        for h in HUMAN:
            print("NEEDS_HUMAN: " + h)
        print("Re-checking...")
        sys.exit(subprocess.call([sys.executable, os.path.abspath(__file__)]))
    ready = not MISSING
    if OPTIONAL:
        print("(optional, not needed to start: " + ", ".join(OPTIONAL) + ")")
    print("READY" if ready else "NOT READY: " + ", ".join(MISSING))
    sys.exit(0 if ready else 1)


if __name__ == "__main__":
    main()
