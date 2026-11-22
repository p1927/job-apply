#!/usr/bin/env python3
"""Build the base resume and one tailored resume per application (markdown + text-based PDF).

Content comes from the tenant file resume-content.json; only facts from candidate-profile.md belong there. Tailoring changes the headline, the summary,
the order of skills and the order of bullets. It never adds a claim.

Usage: python3 tools/make_resumes.py                 # build every stored config
       python3 tools/make_resumes.py spotify         # build one stored config
       python3 tools/make_resumes.py spotify --out applications/APP-006/Jane_Doe_Spotify_Resume
       python3 tools/make_resumes.py --new APP-052 --key acme --company Acme --headline "AI Engineer | RAG" --summary "..."
         (new config copies the base resume's bullet order; out defaults to applications/APP-052/<Name>_<Company>_Resume;
          the PDF path is stored on the app in data/applications.json by default; --record is accepted for old callers)
       python3 tools/make_resumes.py --list | --no-pdf (markdown only)

Env: CHROME_PATH (Chrome binary; default is the macOS app), the tenant comes from tools/tenant.py.
After building it warns about more than two pages, em dashes, banned words and banned claims.
"""
import argparse, html, json, os, pathlib, re, shutil, subprocess, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tenant
import datalock

ROOT = tenant.root()
DEFAULT_CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
CHROME_CANDIDATES = [DEFAULT_CHROME, "/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser",
                     r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                     r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                     "/Applications/Chromium.app/Contents/MacOS/Chromium"]
BANNED_WORDS = ["leverage", "utilize", "spearhead", "results-driven", "passionate", "robust", "seamless"]
BANNED_CLAIMS = []   # filled from resume-content.json


def load_content():
    p = os.path.join(ROOT, "resume-content.json")
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError) as e:
        sys.exit(f"error: cannot read {p}: {e}. Run the setup skill's resume step to create it.")


CONTENT = load_content()
BANNED_CLAIMS = list(CONTENT.get("banned_claims", []))
EXPERIENCE = CONTENT.get("experience", [])
SKILLS = CONTENT.get("skills", {})
PROJECTS = CONTENT.get("projects", {})
CONFIGS = CONTENT.get("configs", {})
META = tenant.tenant_meta(ROOT)


def read_contact():
    """Contact fields from applicant-details.md (table rows '| Label | value |'); tenant.json fills what is missing."""
    c = {"name": META.get("name", ""), "email": META.get("email", ""), "phone": META.get("phone", ""),
         "linkedin": "", "github": "", "location": ""}
    try:
        text = open(os.path.join(ROOT, "applicant-details.md"), encoding="utf-8").read()
    except OSError:
        return c
    rows = {m.group(1).strip().lower(): m.group(2).strip() for m in re.finditer(r"(?m)^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*$", text)}
    def pick(*keys):
        for k in keys:
            if rows.get(k):
                return rows[k]
        return ""
    name = re.sub(r"\s*\(.*?\)", "", pick("legal name")).strip()
    if name: c["name"] = name
    email = pick("email")
    if re.fullmatch(r"[^@\s]+@[^@\s]+", email): c["email"] = email
    first = re.split(r"[(,;]| also ", pick("phone"))[0].strip()
    if first and not first.startswith("("):
        c["phone"] = first
    if CONTENT.get("phone_display"):
        c["phone"] = CONTENT["phone_display"]          # exact spelling to print on the resume
    for key in ("linkedin", "github"):
        v = re.sub(r"^https?://(www\.)?", "", pick(key)).rstrip("/")
        if "." in v: c[key] = v
    loc = pick("residence")
    if loc and len(loc) < 60: c["location"] = loc
    return c


_C = read_contact()
FILE_NAME = re.sub(r"[^A-Za-z0-9]+", "_", _C["name"]).strip("_") or "Resume"
CONTACT = [x for x in (
    " | ".join(p for p in (_C["location"], _C["email"], _C["phone"]) if p),
    " | ".join(p for p in (_C["linkedin"], _C["github"]) if p),
    CONTENT.get("contact_footer", "")) if x]


def build_md(c):
    L = [f"# {_C['name']}", c["headline"], *CONTACT, "", "## Professional Summary", c["summary"], "", "## Professional Experience"]
    for job in EXPERIENCE:
        keys = c.get("select", {}).get(job["id"]) or list(job["bullets"])
        L += [f"**{job['title']}**, {job['company']}, {job['place']} | {job['dates']}"] + ["- " + job["bullets"][k] for k in keys] + [""]
    L += ["## Technical Skills"] + [f"- **{k}:** {SKILLS[k]}" for k in c["skills"]] + [""]
    L += ["## Projects"] + ["- " + PROJECTS[k] for k in c["projects"]] + [""]
    L += ["## Education", *CONTENT.get("education", []), ""]
    return "\n".join(L)


CSS = """@page{size:A4;margin:13mm 15mm}
:root{--ink:#1b1f24;--mute:#5b6570;--accent:#1f4e79;--rule:#cfd6dd}
*{box-sizing:border-box}
body{font-family:Arial,Helvetica,sans-serif;font-size:9.6pt;line-height:1.38;color:var(--ink);margin:0}
header{border-bottom:2px solid var(--accent);padding-bottom:7px;margin-bottom:2px;display:flex;justify-content:space-between;align-items:center;gap:14px}
header .photo{flex:0 0 auto;width:25mm;height:25mm;border-radius:50%;object-fit:cover;border:1px solid var(--rule)}
h1{font-family:Georgia,"Times New Roman",serif;font-size:23pt;font-weight:600;margin:0}
.role{font-size:10.5pt;color:var(--accent);margin:1px 0 4px;font-weight:700}
.contact{font-size:8.3pt;color:var(--mute);margin:0}
h2{font-size:9.4pt;text-transform:uppercase;color:var(--accent);margin:13px 0 5px;padding-bottom:2px;border-bottom:1px solid var(--rule);font-weight:700;break-after:avoid-page}
p{margin:0 0 3px}
.head{display:flex;justify-content:space-between;align-items:baseline;gap:12px;margin-top:8px;break-after:avoid-page}
.head .l{font-size:10.2pt}.head .r{color:var(--mute);font-size:8.9pt;white-space:nowrap}
ul{margin:3px 0 0 15px;padding:0}li{margin:0 0 2.4px;padding-left:1px}li::marker{color:var(--accent)}
.skills{break-inside:avoid}.skills p{display:flex;gap:10px;margin:0 0 2.5px}.skills b{flex:0 0 118px}.skills span{flex:1}"""


HEAD_RE = re.compile(r"^\*\*(.+?)\*\*(.*?)\s*\|\s*(.+)$")


def photo_uri(c):
    """Data URI of the tenant photo when the config asks for one (config key photo: true); None otherwise.
    The file path comes from resume-content.json key 'photo', relative to the tenant folder. Off by default:
    US and many EU employers prefer no photo, so turn it on per config."""
    rel = CONTENT.get("photo")
    if not (c.get("photo") and rel):
        return None
    path = os.path.join(ROOT, rel)
    if not os.path.isfile(path):
        print(f"WARNING photo file not found: {rel}")
        return None
    import base64, mimetypes
    mime = mimetypes.guess_type(path)[0] or "image/jpeg"
    return f"data:{mime};base64," + base64.b64encode(open(path, "rb").read()).decode()


def md_to_html(md, photo=None):
    """Markdown from build_md to a one-column, ATS-safe page: no tables, icons or text boxes; real text only."""
    out, ul, section, header, sk = [], False, "", [], False
    inline = lambda t: re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html.escape(t))
    def flush_header():
        if header:
            img = f"<img class='photo' src='{photo}' alt=''>" if photo else ""
            out.append("<header><div>" + "".join(header) + f"</div>{img}</header>")
            header.clear()
    for line in md.split("\n"):
        if line.startswith("- "):
            m = re.match(r"- \*\*(.+?):\*\*\s*(.*)$", line)
            if section == "skills" and m:
                if ul: out.append("</ul>"); ul = False
                if not sk: out.append("<div class='skills'>"); sk = True
                out.append(f"<p><strong>{html.escape(m.group(1))}</strong><span>{html.escape(m.group(2))}</span></p>")
                continue
            if not ul: out.append("<ul>"); ul = True
            out.append(f"<li>{inline(line[2:])}</li>"); continue
        if ul: out.append("</ul>"); ul = False
        if sk and not line.startswith("- "): out.append("</div>"); sk = False
        if line.startswith("# "):
            header.append(f"<h1>{inline(line[2:])}</h1>")
        elif line.startswith("## "):
            flush_header()
            title = line[3:]
            section = "skills" if "skill" in title.lower() else ""
            out.append(f"<h2>{inline(title)}</h2>")
        elif not out and line.strip():
            header.append(f"<p class='{'role' if len(header) == 1 else 'contact'}'>{inline(line.replace(' | ', ' / ') if len(header) > 1 else line)}</p>")
        elif (m := HEAD_RE.match(line)):
            out.append(f"<div class='head'><div class='l'><strong>{html.escape(m.group(1))}</strong>{html.escape(m.group(2))}</div><div class='r'>{html.escape(m.group(3))}</div></div>")
        elif line.strip():
            out.append(f"<p>{inline(line)}</p>")
    if ul: out.append("</ul>")
    if sk: out.append("</div>")
    flush_header()
    return f"<!doctype html><html lang='en'><head><meta charset='utf-8'><title>{_C['name']} Resume</title><style>{CSS}</style></head><body>{''.join(out)}</body></html>"


def pdf_pages(pdf):
    """Page count: pypdf if importable, else a pure-python scan of the raw PDF. None when unknown."""
    try:
        from pypdf import PdfReader  # optional
        return len(PdfReader(pdf).pages)
    except Exception:
        pass
    try:
        raw = open(pdf, "rb").read()
    except OSError:
        return None
    counts = [int(x) for x in re.findall(rb"/Type\s*/Pages\b[^>]*?/Count\s+(\d+)", raw)] + \
             [int(x) for x in re.findall(rb"/Count\s+(\d+)[^>]*?/Type\s*/Pages\b", raw)]
    if counts:
        return max(counts)
    n = len(re.findall(rb"/Type\s*/Page\b(?!s)", raw))
    return n or None


def quality_warnings(md, pdf_path=None):
    """Return warning strings for the resume text (markdown source) and, when possible, the PDF."""
    w = []
    if "\u2014" in md: w.append("contains an em dash")
    for word in BANNED_WORDS:
        if re.search(r"\b" + re.escape(word), md, re.I): w.append(f"contains banned word '{word}'")
    for claim in BANNED_CLAIMS:
        if claim.lower() in md.lower(): w.append(f"contains banned claim '{claim}'")
    if pdf_path and os.path.exists(pdf_path):
        n = pdf_pages(pdf_path)
        if n is None: w.append("could not count PDF pages")
        elif n > 2: w.append(f"PDF has {n} pages (limit is 2)")
        try:
            from pypdf import PdfReader  # optional text check of the real PDF
            text = " ".join((p.extract_text() or "") for p in PdfReader(pdf_path).pages)
            if "\u2014" in text and "contains an em dash" not in w: w.append("PDF text contains an em dash")
        except Exception:
            pass
    return w


def chrome_path():
    p = os.environ.get("CHROME_PATH") or next((c for c in CHROME_CANDIDATES if os.path.isfile(c)), DEFAULT_CHROME)
    if not (os.path.isfile(p) and os.access(p, os.X_OK)):
        sys.exit(f"error: Chrome not found or not executable at {p}. Set CHROME_PATH to the Chrome binary, or use --no-pdf.")
    return p


def build(name, out=None, pdf=True):
    c = dict(CONFIGS[name])
    if out: c["out"] = out
    base = os.path.join(ROOT, c["out"])
    os.makedirs(os.path.dirname(base), exist_ok=True)
    md = build_md(c)
    datalock.atomic_write(base + ".md", md, root=ROOT)
    warns = quality_warnings(md)
    if pdf:
        with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
            f.write(md_to_html(md, photo_uri(c))); tmp = f.name
        prof = tempfile.mkdtemp(prefix="resume-chrome-")      # own profile: no clash with other Chrome windows or agents
        pdf_path = base + ".pdf"
        if os.path.exists(pdf_path): os.unlink(pdf_path)       # a stale file must not count as success
        try:
            err = b""
            for attempt in (1, 2):
                try:
                    r = subprocess.run([chrome_path(), "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                                        f"--user-data-dir={prof}", f"--print-to-pdf={pdf_path}", pathlib.Path(tmp).as_uri()],
                                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=60)
                    err = r.stderr or b""
                except subprocess.TimeoutExpired:
                    err = b"timeout after 60 s"
                # Chrome may print a teardown warning and exit non-zero AFTER writing a good PDF: trust the file.
                if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 1000:
                    break
            else:
                sys.exit(f"error: Chrome did not produce {c['out']}.pdf after 2 tries: {err.decode(errors='replace')[-300:]}. "
                         "Use --no-pdf to build the markdown only.")
        finally:
            if os.path.exists(tmp): os.unlink(tmp)
            shutil.rmtree(prof, ignore_errors=True)
        warns = quality_warnings(md, base + ".pdf")
    print("built", c["out"] + (".pdf" if pdf else ".md"))
    for x in warns:
        print(f"WARNING {c['out']}: {x}")
    return c["out"]


def new_config(app_id, key, company, headline, summary):
    if not re.fullmatch(r"APP-\d{3,}", app_id): sys.exit("error: --new needs an id like APP-052")
    if key in CONFIGS:
        if CONFIGS[key].get("out", "").startswith(f"applications/{app_id}/"):
            return                                  # same app, same key: rebuild instead of failing
        sys.exit(f"error: config '{key}' already exists for another application; pick another --key")
    co = re.sub(r"[^A-Za-z0-9]", "", company or key.title())
    if "base" not in CONFIGS: sys.exit("error: resume-content.json has no 'base' config to copy")
    b = CONFIGS["base"]
    CONFIGS[key] = dict(out=f"applications/{app_id}/{FILE_NAME}_{co}_Resume", headline=headline, summary=summary,
                        select={k: list(v) for k, v in b.get("select", {}).items()}, skills=list(b["skills"]), projects=list(b["projects"]))
    save_config(key)


def save_config(key):
    """Persist a new config into the tenant's resume-content.json so it can be rebuilt later."""
    p = os.path.join(ROOT, "resume-content.json")
    doc = load_content()
    doc.setdefault("configs", {})[key] = CONFIGS[key]
    datalock.atomic_write(p, json.dumps(doc, indent=1, ensure_ascii=False) + "\n", root=ROOT)


def record_resume(app_id, out):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import ledger_set as L
    print("PDF:", out + ".pdf")                      # printed first so the work is not lost if recording fails
    with L.locked():
        d = L.load_apps()
        app = next((x for x in d["apps"] if x["id"] == app_id), None)
        if app is None: sys.exit(f"error: {app_id} is not in data/applications.json (the PDF above was built; create the app with tools/new_app.py)")
        app["resume"] = out + ".pdf"
        L.atomic_write(L.path("data/applications.json"), L.dump_apps(d))
    print("recorded resume path on", app_id)


def main():
    ap = argparse.ArgumentParser(description="Build tailored resumes.")
    ap.add_argument("names", nargs="*"); ap.add_argument("--out"); ap.add_argument("--list", action="store_true")
    ap.add_argument("--no-pdf", action="store_true"); ap.add_argument("--record", action="store_true")
    ap.add_argument("--new"); ap.add_argument("--key"); ap.add_argument("--company")
    ap.add_argument("--headline"); ap.add_argument("--summary")
    a = ap.parse_args()
    if a.list:
        print("\n".join(CONFIGS)); return
    names = a.names
    if a.new:
        if not (a.key and a.headline and a.summary): sys.exit("error: --new needs --key, --headline and --summary")
        new_config(a.new, a.key, a.company, a.headline, a.summary)
        names = [a.key]
    if a.out and len(names) != 1: sys.exit("error: --out needs exactly one config name")
    for n in names or list(CONFIGS):
        if n not in CONFIGS: sys.exit(f"error: unknown config '{n}'. Known: {', '.join(CONFIGS)}")
        out = build(n, a.out, pdf=not a.no_pdf)
        if a.new and not a.no_pdf: record_resume(a.new, out)   # --record is still accepted; recording is the default for --new


if __name__ == "__main__":
    main()
