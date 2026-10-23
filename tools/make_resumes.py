#!/usr/bin/env python3
"""Build the base resume and one tailored resume per application (markdown + text-based PDF).

Content comes from the tenant file resume-content.json; only facts from candidate-profile.md belong there. Tailoring changes the headline, the summary,
the order of skills and the order of bullets. It never adds a claim.

Usage: python3 tools/make_resumes.py                 # build every stored config
       python3 tools/make_resumes.py spotify         # build one stored config
       python3 tools/make_resumes.py spotify --out applications/APP-006/Jane_Doe_Spotify_Resume
       python3 tools/make_resumes.py --new APP-052 --key acme --company Acme --headline "AI Engineer | RAG" --summary "..."
         (new config copies the base resume's bullet order; out defaults to applications/APP-052/<Name>_<Company>_Resume;
          add --record to store the PDF path on the app in data/applications.json)
       python3 tools/make_resumes.py --list | --no-pdf (markdown only)

Env: CHROME_PATH (Chrome binary; default is the macOS app), the tenant comes from tools/tenant.py.
After building it warns about more than two pages, em dashes, banned words and banned claims.
"""
import argparse, html, json, os, re, subprocess, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tenant

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


CSS = """@page{size:A4;margin:14mm 16mm}
body{font-family:Arial,Helvetica,sans-serif;font-size:10.5pt;line-height:1.32;color:#111;margin:0}
h1{font-size:18pt;margin:0 0 2px}h2{font-size:11.5pt;margin:12px 0 4px;border-bottom:1px solid #888;padding-bottom:1px}
p{margin:2px 0}ul{margin:2px 0 6px 18px;padding:0}li{margin:1.5px 0}"""


def md_to_html(md):
    out, ul = [], False
    inline = lambda t: re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html.escape(t))
    for line in md.split("\n"):
        if line.startswith("- "):
            if not ul: out.append("<ul>"); ul = True
            out.append(f"<li>{inline(line[2:])}</li>"); continue
        if ul: out.append("</ul>"); ul = False
        if line.startswith("# "): out.append(f"<h1>{inline(line[2:])}</h1>")
        elif line.startswith("## "): out.append(f"<h2>{inline(line[3:])}</h2>")
        elif line.strip(): out.append(f"<p>{inline(line)}</p>")
    if ul: out.append("</ul>")
    return f"<!doctype html><html><head><meta charset='utf-8'><title>{_C['name']} Resume</title><style>{CSS}</style></head><body>{''.join(out)}</body></html>"


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
    open(base + ".md", "w", encoding="utf-8", newline="\n").write(md)
    warns = quality_warnings(md)
    if pdf:
        with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
            f.write(md_to_html(md)); tmp = f.name
        try:
            subprocess.run([chrome_path(), "--headless", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={base}.pdf", __import__("pathlib").Path(tmp).as_uri()],
                           stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True, timeout=60)
        except subprocess.TimeoutExpired:
            sys.exit(f"error: Chrome took longer than 60 seconds building {c['out']}.pdf")
        except subprocess.CalledProcessError as e:
            sys.exit(f"error: Chrome failed building {c['out']}.pdf: {(e.stderr or b'').decode(errors='replace')[-300:]}")
        finally:
            if os.path.exists(tmp): os.unlink(tmp)
        if not os.path.exists(base + ".pdf"):
            sys.exit(f"error: Chrome ran but {c['out']}.pdf was not created")
        warns = quality_warnings(md, base + ".pdf")
    print("built", c["out"] + (".pdf" if pdf else ".md"))
    for x in warns:
        print(f"WARNING {c['out']}: {x}")
    return c["out"]


def new_config(app_id, key, company, headline, summary):
    if key in CONFIGS: sys.exit(f"error: config '{key}' already exists; pick another --key or build it by name")
    if not re.fullmatch(r"APP-\d{3,}", app_id): sys.exit("error: --new needs an id like APP-052")
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
    tmp = p + ".part"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(doc, f, indent=1, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, p)


def record_resume(app_id, out):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import ledger_set as L
    d = L.load_apps()
    app = next((x for x in d["apps"] if x["id"] == app_id), None)
    if app is None: sys.exit(f"error: {app_id} is not in data/applications.json")
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
        if a.record and a.new: record_resume(a.new, out)


if __name__ == "__main__":
    main()
