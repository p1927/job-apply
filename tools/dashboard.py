#!/usr/bin/env python3
"""Live, read-only dashboard for the active tenant. Claude starts it; the person just looks and clicks.

    python3 tools/dashboard.py              start (or reuse) the dashboard and open it in the default browser
    python3 tools/dashboard.py --no-open    same, without opening a browser (prints the address)
    python3 tools/dashboard.py --stop       stop a running dashboard for this tenant

How it works
- A tiny local web server (Python standard library only, bound to 127.0.0.1) serves templates/dashboard/ and the
  active tenant's state as JSON (/api/state). It reads the tenant's files on every change, never writes them.
- The page keeps one open connection (/events). When any tenant file changes the server tells the page, the page
  refetches and redraws. When the tab is closed the connection drops and the server exits after a short grace period.
- "Ask Claude" copies a ready-made message to the clipboard and brings the Claude app to the front.
- Files are served only from inside the tenant folder, only a fixed set of file types, and the ask action needs a
  per-run token, so another web page cannot drive it.
Env: JOBS_TENANT / JOBS_ROOT select the tenant (see tenant.py). DASH_IDLE_SECONDS (default 25) is the grace period.
"""
import csv
import datetime
import hashlib
import http.server
import json
import mimetypes
import os
import secrets
import socketserver
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
import webbrowser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tenant

ROOT = tenant.root()
META = tenant.tenant_meta(ROOT)
UI = tenant.engine_path("templates", "dashboard")
LOCK = os.path.join(ROOT, "board", ".dashboard.json")
TOKEN = secrets.token_urlsafe(24)
IDLE = float(os.environ.get("DASH_IDLE_SECONDS") or 25)
FIRST_VISIT_WAIT = 120
SERVABLE = {".md", ".pdf", ".json", ".csv", ".txt", ".html"}
FOLLOW_STATUSES = ("Applied", "Screening")
APP_DEFAULTS = {"company": "", "role": "", "track": "software", "location": "", "mode": "", "bigTech": False, "fit": "weak",
                "pay": "", "checks": [], "learn": [], "link": "", "links": [], "resume": "", "detail": "", "status": "Shortlisted",
                "dateFound": "", "dateApplied": "", "notes": "", "tag": "", "verdict": "check", "category": "Other", "blocker": ""}
WATCH_FILES = ("REQUIREMENTS.md", "candidate-profile.md", "resume-content.json", "resume.md", "tenant.json", "data", "applications")
SKIP_DIRS = {"node_modules", ".git", "career-ops", "board"}


def today():
    return os.environ.get("JOBS_TODAY") or str(datetime.date.today())


def read_text(rel, default=""):
    try:
        with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
            return f.read()
    except OSError:
        return default


def read_json(rel, default):
    try:
        return json.loads(read_text(rel) or "null") or default
    except ValueError:
        return default


def add_days(day, n):
    try:
        return str(datetime.date.fromisoformat(day) + datetime.timedelta(days=n))
    except (ValueError, TypeError):
        return ""


def follow_up(a):
    if a["status"] not in FOLLOW_STATUSES:
        return None
    fu = a.get("followUp") if isinstance(a.get("followUp"), dict) else {}
    day = fu.get("nextCheck") or add_days(a["dateApplied"], 7)
    if not day:
        return None
    t = today()
    return {"date": day, "state": "overdue" if day < t else "due" if day == t else "upcoming"}


def exists(rel):
    return bool(rel) and os.path.isfile(os.path.join(ROOT, rel))


def files_for(app_id):
    """Company file, saved posting and resume files that exist for an application."""
    out = {"detail": "", "posting": "", "resumes": []}
    for rel in (f"applications/{app_id}.md",):
        if exists(rel):
            out["detail"] = rel
    for rel in (f"applications/{app_id}-posting.md",):
        if exists(rel):
            out["posting"] = rel
    d = os.path.join(ROOT, "applications", app_id)
    if os.path.isdir(d):
        for n in sorted(os.listdir(d)):
            if os.path.splitext(n)[1].lower() in (".pdf", ".md"):
                out["resumes"].append(f"applications/{app_id}/{n}")
    return out


def read_ledger(vocab):
    p = os.path.join(ROOT, "data", "seen-jobs.csv")
    try:
        with open(p, encoding="utf-8", newline="") as f:
            return [{k: (v or "").strip() for k, v in r.items() if k} for r in csv.DictReader(f)]
    except OSError:
        return []


def requirement_sections():
    """REQUIREMENTS.md split into [{title, body}] on '## ' headings; text before the first one is the intro."""
    text = read_text("REQUIREMENTS.md")
    intro, sections, cur = [], [], None
    for line in text.splitlines():
        if line.startswith("## "):
            cur = {"title": line[3:].strip(), "body": []}
            sections.append(cur)
        elif cur is None:
            intro.append(line)
        else:
            cur["body"].append(line)
    return {"intro": "\n".join(intro).strip(), "sections": [{"title": s["title"], "body": "\n".join(s["body"]).strip()} for s in sections]}


def build_state():
    vocab = tenant.load_vocab(ROOT)
    data = read_json("data/applications.json", {})
    apps = []
    for a in data.get("apps", []):
        n = dict(APP_DEFAULTS)
        n.update({k: v for k, v in a.items() if v is not None})
        n["fu"] = follow_up(n)
        n["files"] = files_for(n["id"])
        if n["resume"] and not exists(n["resume"]):
            n["resumeMissing"] = True
        apps.append(n)
    ledger = read_ledger(vocab)
    base_resumes = [r for r in ("resume.pdf", "resume.md") if exists(r)]
    app_order = list(vocab.get("app_status") or [])
    app_order += [s for s in dict.fromkeys(a["status"] for a in apps) if s not in app_order]
    labels = dict(META.get("track_labels") or {})
    track_keys = list(vocab.get("tracks") or labels)
    track_keys += [t for t in dict.fromkeys(a["track"] for a in apps) if t not in track_keys]
    needs = [{"kind": "ledger", "id": r.get("job_id", ""), "company": r.get("company", ""), "title": r.get("title", ""),
              "blocker": r["blocker"], "app": r.get("app_id", "")} for r in ledger if r.get("blocker")]
    seen_apps = {n["app"] for n in needs}
    needs += [{"kind": "app", "id": a["id"], "company": a["company"], "title": a["role"], "blocker": a["blocker"], "app": a["id"]}
              for a in apps if a["blocker"] and a["id"] not in seen_apps]
    return {
        "tenant": {"id": META.get("id", ""), "name": META.get("name", "")},
        "today": today(),
        "requirements": requirement_sections(),
        "requirementSummary": data.get("requirements") or {},
        "requirementLabels": META.get("requirement_labels") or {},
        "profile": read_text("candidate-profile.md"),
        "apps": apps,
        "left": data.get("left") or [],
        "ledger": ledger,
        "needs": needs,
        "vocab": {"appOrder": app_order, "ledgerStatus": vocab.get("ledger_status", []), "reasons": vocab.get("ledger_reason_codes", []),
                  "categoryNotes": vocab.get("category_notes", {})},
        "tracks": [[k, labels.get(k, k)] for k in track_keys],
        "baseResumes": base_resumes,
        "followUp": META.get("followup") or {},
        "links": {"repo": data.get("repo", ""), "projectBoard": data.get("projectBoard", "")},
    }


def watch_signature():
    """A cheap fingerprint of every tenant file the dashboard shows: changes whenever one is added, edited or removed."""
    h = hashlib.sha1()
    for name in WATCH_FILES:
        p = os.path.join(ROOT, name)
        if os.path.isfile(p):
            st = os.stat(p)
            h.update(f"{name}:{st.st_mtime_ns}:{st.st_size};".encode())
        elif os.path.isdir(p):
            for dp, dns, fns in os.walk(p):
                dns[:] = sorted(d for d in dns if d not in SKIP_DIRS)
                for fn in sorted(fns):
                    if fn.startswith("."):
                        continue
                    fp = os.path.join(dp, fn)
                    try:
                        st = os.stat(fp)
                    except OSError:
                        continue
                    h.update(f"{os.path.relpath(fp, ROOT)}:{st.st_mtime_ns}:{st.st_size};".encode())
    return h.hexdigest()[:12]


class Hub:
    """Shared state: current version, number of open pages, and when the last one left."""

    def __init__(self):
        self.cv = threading.Condition()
        self.version = watch_signature()
        self.clients = 0
        self.seen_client = False
        self.last_gone = time.time()
        self.started = time.time()
        self.stop = False

    def poll(self):
        while not self.stop:
            time.sleep(0.7)
            sig = watch_signature()
            with self.cv:
                if sig != self.version:
                    self.version = sig
                    self.cv.notify_all()
                idle_for = time.time() - self.last_gone
                if self.clients == 0 and ((self.seen_client and idle_for > IDLE) or (not self.seen_client and time.time() - self.started > FIRST_VISIT_WAIT)):
                    self.stop = True
                    self.cv.notify_all()
                    threading.Thread(target=SERVER.shutdown, daemon=True).start()


HUB = Hub()
SERVER = None


def focus_claude(text):
    """Copy text to the clipboard and bring the Claude app forward. Returns (focused, copied)."""
    copied = focused = False
    try:
        if sys.platform == "darwin":
            copied = subprocess.run(["pbcopy"], input=text.encode("utf-8"), timeout=5).returncode == 0
            focused = subprocess.run(["open", "-a", "Claude"], capture_output=True, timeout=10).returncode == 0
        elif sys.platform.startswith("win"):
            copied = subprocess.run(["clip"], input=text.encode("utf-16le"), timeout=5).returncode == 0
            focused = subprocess.run(["cmd", "/c", "start", "", "claude:"], capture_output=True, timeout=10).returncode == 0
        else:
            for cmd in (["wl-copy"], ["xclip", "-selection", "clipboard"]):
                try:
                    if subprocess.run(cmd, input=text.encode("utf-8"), timeout=5).returncode == 0:
                        copied = True
                        break
                except OSError:
                    continue
    except (OSError, subprocess.SubprocessError):
        pass
    return focused, copied


class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "JobDashboard"
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def host_ok(self):
        host = (self.headers.get("Host") or "").split(":")[0].lower()
        return host in ("127.0.0.1", "localhost", "[::1]")

    def send_bytes(self, code, body, ctype, extra=None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, code, obj):
        self.send_bytes(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def do_GET(self):
        if not self.host_ok():
            return self.send_json(403, {"error": "bad host"})
        u = urllib.parse.urlparse(self.path)
        path = u.path
        if path in ("/", "/index.html"):
            return self.static("index.html", token=True)
        if path == "/api/ping":
            return self.send_json(200, {"ok": True, "tenant": META.get("id", ""), "pid": os.getpid()})
        if path == "/api/state":
            state = build_state()
            state["version"] = HUB.version
            return self.send_json(200, state)
        if path == "/api/file":
            return self.tenant_file(urllib.parse.parse_qs(u.query).get("path", [""])[0])
        if path == "/events":
            return self.events()
        if path.startswith("/ui/"):
            return self.static(path[4:])
        self.send_json(404, {"error": "not found"})

    def do_POST(self):
        if not self.host_ok():
            return self.send_json(403, {"error": "bad host"})
        origin = self.headers.get("Origin") or ""
        if origin and urllib.parse.urlparse(origin).hostname not in ("127.0.0.1", "localhost", "::1"):
            return self.send_json(403, {"error": "bad origin"})
        if self.headers.get("X-Dashboard-Token") != TOKEN:
            return self.send_json(403, {"error": "bad token"})
        n = min(int(self.headers.get("Content-Length") or 0), 20000)
        try:
            body = json.loads(self.rfile.read(n) or b"{}")
        except ValueError:
            return self.send_json(400, {"error": "bad json"})
        if self.path == "/api/ask":
            text = str(body.get("text") or "").strip()[:4000]
            if not text:
                return self.send_json(400, {"error": "empty"})
            focused, copied = focus_claude(text)
            return self.send_json(200, {"ok": True, "copied": copied, "focused": focused})
        self.send_json(404, {"error": "not found"})

    def static(self, rel, token=False):
        p = os.path.realpath(os.path.join(UI, rel))
        if not p.startswith(os.path.realpath(UI) + os.sep) or not os.path.isfile(p):
            return self.send_json(404, {"error": "not found"})
        with open(p, "rb") as f:
            body = f.read()
        if token:
            body = body.replace(b"__DASH_TOKEN__", TOKEN.encode())
        ctype = mimetypes.guess_type(p)[0] or "application/octet-stream"
        self.send_bytes(200, body, ctype + ("; charset=utf-8" if ctype.startswith("text/") or ctype.endswith("javascript") else ""))

    def tenant_file(self, rel):
        ext = os.path.splitext(rel)[1].lower()
        p = os.path.realpath(os.path.join(ROOT, rel))
        if not rel or ext not in SERVABLE or not tenant.inside(p, ROOT) or not os.path.isfile(p) or "/." in "/" + rel:
            return self.send_json(404, {"error": "not found"})
        with open(p, "rb") as f:
            body = f.read()
        ctype = "application/pdf" if ext == ".pdf" else "text/plain; charset=utf-8"
        self.send_bytes(200, body, ctype, {"Content-Disposition": "inline"})

    def events(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        with HUB.cv:
            HUB.clients += 1
            HUB.seen_client = True
            seen = HUB.version
        try:
            self.wfile.write(f"event: hello\ndata: {seen}\n\n".encode())
            self.wfile.flush()
            beat = 0
            while not HUB.stop:
                with HUB.cv:
                    HUB.cv.wait(timeout=5)
                    ver = HUB.version
                if ver != seen:
                    seen = ver
                    self.wfile.write(f"event: change\ndata: {ver}\n\n".encode())
                else:
                    beat += 1
                    self.wfile.write(b": beat\n\n")
                self.wfile.flush()
        except (OSError, ValueError):
            pass
        finally:
            with HUB.cv:
                HUB.clients -= 1
                HUB.last_gone = time.time()


class Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def handle_error(self, request, client_address):
        """A page that closes mid-request is normal; stay quiet about it."""
        if not isinstance(sys.exc_info()[1], (ConnectionError, TimeoutError)):
            super().handle_error(request, client_address)


def running():
    """Address of a dashboard already running for this tenant, or ''."""
    try:
        with open(LOCK, encoding="utf-8") as f:
            info = json.load(f)
        url = f"http://127.0.0.1:{int(info['port'])}"
        with urllib.request.urlopen(url + "/api/ping", timeout=1.5) as r:
            ok = json.load(r).get("tenant") == META.get("id", "")
        return url if ok else ""
    except (OSError, ValueError, KeyError, TypeError):
        return ""


def stop_running():
    try:
        with open(LOCK, encoding="utf-8") as f:
            pid = int(json.load(f)["pid"])
        os.kill(pid, 15)
        print("stopped dashboard", pid)
    except (OSError, ValueError, KeyError):
        print("no dashboard running")


def main():
    global SERVER
    args = sys.argv[1:]
    if "--stop" in args:
        return stop_running()
    url = running()
    if url:
        print("dashboard already running:", url)
        if "--no-open" not in args:
            webbrowser.open(url)
        return
    SERVER = Server(("127.0.0.1", int(os.environ.get("DASH_PORT") or 0)), Handler)
    port = SERVER.server_address[1]
    url = f"http://127.0.0.1:{port}"
    os.makedirs(os.path.dirname(LOCK), exist_ok=True)
    with open(LOCK, "w", encoding="utf-8") as f:
        json.dump({"port": port, "pid": os.getpid(), "tenant": META.get("id", "")}, f)
    threading.Thread(target=HUB.poll, daemon=True).start()
    print("dashboard:", url, flush=True)
    if "--no-open" not in args:
        webbrowser.open(url)
    try:
        SERVER.serve_forever(poll_interval=0.3)
    except KeyboardInterrupt:
        pass
    finally:
        HUB.stop = True
        try:
            os.unlink(LOCK)
        except OSError:
            pass
        print("dashboard closed")


if __name__ == "__main__":
    main()
