#!/usr/bin/env python3
"""Self-test for ledger_set, new_company_file, record_application, make_resumes and build_board.

Runs everything on a synthetic tenant (fake person "Jane Doe", built from tenants/_template) in a temp directory with
its own throwaway git repo (no remote, so nothing can be pushed). No real tenant is read or written, so the suite
works on any machine, including one with no tenant yet.
Usage: python3 tools/test_tools.py        (env TEST_SCRATCH=dir to choose where the copy goes)
"""
import csv, hashlib, json, os, shutil, subprocess, sys, tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE = os.path.join(REPO, 'tenants', '_template')
TOOLS = os.path.join(REPO, "tools")
FAILS, PASSES = [], 0


def check(name, cond, detail=""):
    global PASSES
    if cond:
        PASSES += 1
        print("ok   ", name)
    else:
        FAILS.append(name)
        print("FAIL ", name, detail)


def run(root, tool, *args, env=None):
    e = {**os.environ, "JOBS_ROOT": root, "JOBS_TODAY": "2026-10-23", **(env or {})}
    e.pop("JOBS_PUSH", None)
    p = subprocess.run([sys.executable, os.path.join(TOOLS, tool), *args], capture_output=True, text=True, env=e, cwd=root)
    return p.returncode, p.stdout + p.stderr


def rd(root, rel):
    with open(os.path.join(root, rel), encoding="utf-8", newline="") as f:
        return f.read()


def wr(root, rel, text):
    p = os.path.join(root, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def md5(root, rel):
    return hashlib.md5(rd(root, rel).encode()).hexdigest()


def git(root, *a):
    return subprocess.run(["git", *a], cwd=root, capture_output=True, text=True).stdout


FIXTURE_DETAILS = """# Applicant Details (fixture)

## Personal
| Field | Value |
| --- | --- |
| Legal name | Jane Doe |
| Email | jane.doe@example.test |
| Phone | +46 701234567 |
| LinkedIn | https://www.linkedin.com/in/jane-doe-test/ |
| GitHub | https://github.com/janedoe-test |
| Residence | Testville, Testland |

## Learned answers
| Question pattern | Answer | Learned (date) | Where seen |
| --- | --- | --- | --- |
"""

FIXTURE_CONTENT = {
    "contact_footer": "Work authorization line.", "banned_claims": ["35%"],
    "experience": [{"id": "j1", "title": "Engineer", "company": "Acme", "place": "Testville", "dates": "Jan 2020 - Present",
                    "bullets": {"a": "Built the first thing.", "b": "Built the second thing."}}],
    "skills": {"Core": "Python, testing"}, "projects": {"p": "**Proj:** a project."}, "education": ["**Uni**, Testland | 2010 - 2014"],
    "configs": {"base": {"out": "resume", "headline": "Engineer | Testing", "summary": "Engineer with years of experience.",
                         "select": {"j1": ["a", "b"]}, "skills": ["Core"], "projects": ["p"]}}}


def make_copy():
    base = os.environ.get("TEST_SCRATCH") or tempfile.gettempdir()
    root = tempfile.mkdtemp(prefix="jobs-test-", dir=base)
    if os.path.realpath(root).startswith(os.path.realpath(REPO)):
        sys.exit("refusing to test inside the real repo")
    shutil.rmtree(root)
    shutil.copytree(TEMPLATE, root)
    for dp, _, fns in os.walk(root):
        for fn in fns:
            p = os.path.join(dp, fn)
            try:
                s = open(p, encoding="utf-8").read()
            except UnicodeDecodeError:
                continue
            open(p, "w", encoding="utf-8", newline="\n").write(s.replace("{{NAME}}", "Jane Doe").replace("{{ID}}", "jane-doe"))
    meta = json.loads(rd(root, "tenant.json"))
    meta.update({"git_name": "Test", "git_email": "t@t.test", "email": "jane.doe@example.test", "phone": "+46 701234567"})
    wr(root, "tenant.json", json.dumps(meta, indent=1) + "\n")
    wr(root, "applicant-details.md", FIXTURE_DETAILS)
    wr(root, "resume-content.json", json.dumps(FIXTURE_CONTENT, indent=1))
    wr(root, "data/seen-jobs.csv", "job_id,category,company,title,location,workplace,status,reason,blocker,app_id,source,note\n"
       "1001,Local,Alpha,AI Engineer,Testville,Hybrid,New,,,,linkedin,\n1002,Remote,Beta,ML Engineer,Remote,Remote,New,,,,linkedin,\n"
       "1003,Local,Gamma,Data Analyst,Testville,On-site,Not-relevant,not-ai,,,company,not the field\n")
    wr(root, "applications/APP-001.md", "# APP-001 : Alpha : AI Engineer\n\n- Status: Shortlisted\n")
    d = json.loads(rd(root, "data/applications.json"))
    d["requirements"] = {"pay": "fixture pay"}
    wr(root, "data/applications.json", json.dumps(d, indent=1) + "\n")
    return root


def add_test_app(root, app_id="APP-900", link="https://www.linkedin.com/jobs/view/9990001/"):
    d = json.loads(rd(root, "data/applications.json"))
    d["apps"].append({"id": app_id, "company": "TestCo", "role": "AI Engineer", "track": "primary", "location": "Remote",
                      "mode": "Remote", "bigTech": False, "fit": "weak", "pay": "", "checks": [], "learn": [], "link": link,
                      "links": [], "resume": "", "detail": "", "status": "Shortlisted", "dateFound": "2026-10-22",
                      "dateApplied": "", "notes": "", "tag": "", "verdict": "check", "category": "Other", "blocker": "",
                      "followUp": {"nextCheck": "", "lastCheck": ""}})
    wr(root, "data/applications.json", json.dumps(d, indent=1, ensure_ascii=False) + "\n")


def tenant_vocab():
    sys.path.insert(0, TOOLS)
    import tenant
    return tenant.load_vocab(TEMPLATE)


def ledger(root):
    with open(os.path.join(root, "data/seen-jobs.csv"), encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def test_ledger(root):
    vocab = tenant_vocab()
    rows = ledger(root)
    jid = next(r for r in rows if r["status"] == "New" and not r["reason"])["job_id"]
    before = md5(root, "data/seen-jobs.csv")
    rc, out = run(root, "ledger_set.py", jid, "--status", "Bogus")
    check("ledger: invalid status rejected", rc != 0 and "vocab" in out and md5(root, "data/seen-jobs.csv") == before, out)
    rc, out = run(root, "ledger_set.py", jid, "--status", "Not-relevant")
    check("ledger: Not-relevant without reason rejected", rc != 0, out)
    rc, out = run(root, "ledger_set.py", jid, "--status", "Relevant", "--blocker", "bogus")
    check("ledger: invalid blocker rejected", rc != 0, out)
    rc, out = run(root, "ledger_set.py", jid, "--status", "Relevant", "--blocker", "account", "--note", "needs login")
    r = next(x for x in ledger(root) if x["job_id"] == jid)
    check("ledger: valid update", rc == 0 and r["status"] == "Relevant" and r["blocker"] == "account" and r["note"] == "needs login", out)
    check("ledger: LF only, header intact", "\r" not in rd(root, "data/seen-jobs.csv") and rd(root, "data/seen-jobs.csv").startswith(",".join(vocab["csv_header"]) + "\n"))
    rc, out = run(root, "ledger_set.py", jid, "--status", "Not-relevant", "--reason", "location")
    r = next(x for x in ledger(root) if x["job_id"] == jid)
    check("ledger: leaving for Not-relevant clears blocker", rc == 0 and r["blocker"] == "" and r["reason"] == "location", out)
    rc, out = run(root, "ledger_set.py", "no-such-id", "--status", "New")
    check("ledger: unknown id fails without --add", rc != 0 and "not found" in out, out)
    rc, out = run(root, "ledger_set.py", "9990001", "--add", "--company", "TestCo", "--title", "AI Engineer", "--location", "Remote", "--workplace", "Remote", "--source", "company")
    r = next((x for x in ledger(root) if x["job_id"] == "9990001"), None)
    check("ledger: --add creates New row", rc == 0 and r and r["status"] == "New" and r["company"] == "TestCo" and r["workplace"] == "Remote", out)
    rc, out = run(root, "ledger_set.py", "9990002", "--add", "--title", "x")
    check("ledger: --add without company on new id fails", rc != 0 and not any(r["job_id"] == "9990002" for r in ledger(root)), out)
    rc, out = run(root, "ledger_set.py", "9990001", "Relevant", "positional note", "Remote")
    r = next(x for x in ledger(root) if x["job_id"] == "9990001")
    check("ledger: legacy positional form", rc == 0 and r["status"] == "Relevant" and r["note"] == "positional note" and r["category"] == "Remote", out)
    rc, out = run(root, "ledger_set.py", "9990001", "Skip-SWE", "old style")
    r = next(x for x in ledger(root) if x["job_id"] == "9990001")
    check("ledger: legacy Skip-X maps to Not-relevant + reason", rc == 0 and r["status"] == "Not-relevant" and r["reason"] == "other", out)
    rc, out = run(root, "ledger_set.py", "9990001", "Relevant - needs account", "x")
    check("ledger: old status string rejected", rc != 0, out)
    # short rows tolerated
    text = rd(root, "data/seen-jobs.csv") + "123456,Local,ShortCo,Short row\n"
    wr(root, "data/seen-jobs.csv", text)
    rc, out = run(root, "ledger_set.py", "123456", "--status", "Closed")
    r = next((x for x in ledger(root) if x["job_id"] == "123456"), None)
    check("ledger: short row tolerated", rc == 0 and r and r["status"] == "Closed" and r["note"] == "", out)
    # atomic: a failing os.replace leaves the file untouched and no temp files
    before = md5(root, "data/seen-jobs.csv")
    code = ("import os,sys; os.environ['JOBS_ROOT']=%r; sys.path.insert(0,%r); import ledger_set as L\n"
            "def boom(a,b): raise OSError('disk full')\nL.os.replace=boom\n"
            "v=L.load_vocab(); rows=L.read_ledger(v); L.apply_update(v,rows,rows[0]['job_id'],status='New'); L.save_ledger(rows,v)\n") % (root, TOOLS)
    p = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    left = [f for f in os.listdir(os.path.join(root, "data")) if f.endswith(".part")]
    check("ledger: atomic write (failed replace keeps old file, no temp left)", p.returncode != 0 and md5(root, "data/seen-jobs.csv") == before and not left, p.stderr[-200:])
    # old header gives a clear error
    saved = rd(root, "data/seen-jobs.csv")
    wr(root, "data/seen-jobs.csv", "job_id,category,company,title,location,workplace,status,note\n1,a,b,c,d,e,New,\n")
    rc, out = run(root, "ledger_set.py", "1", "--status", "New")
    check("ledger: old header gives clear message", rc != 0 and "header" in out, out)
    wr(root, "data/seen-jobs.csv", saved)


def test_company_file(root):
    add_test_app(root)
    rc, out = run(root, "new_company_file.py", "APP-900")
    check("company: no text and no --stub fails", rc != 0 and "no posting text" in out, out)
    rc, out = run(root, "new_company_file.py", "APP-900", "--stub")
    d = json.loads(rd(root, "data/applications.json"))
    app = next(a for a in d["apps"] if a["id"] == "APP-900")
    t = rd(root, "applications/APP-900.md")
    check("company: stub creates posting + file from template + sets detail", rc == 0 and app["detail"] == "applications/APP-900.md"
          and os.path.exists(os.path.join(root, "applications/APP-900-posting.md")) and "APP-900" in t and "APP-###" not in t, out)
    heads = ["Open questions for round 1", "Posting", "Contacts", "Interview log", "Outcome", "Learnings"]
    check("company: all six sections present", all(("## " + h) in t for h in heads), t)
    post = rd(root, "applications/APP-900-posting.md")
    open(os.path.join(root, "job.txt"), "w").write("Real job text.\n")
    rc, out = run(root, "new_company_file.py", "APP-900", "job.txt")
    check("company: overwrite of posting refused", rc != 0 and "already exists" in out and rd(root, "applications/APP-900-posting.md") == post, out)
    rc, out = run(root, "new_company_file.py", "APP-900", "job.txt", "--force")
    check("company: --force overwrites posting", rc == 0 and "Real job text." in rd(root, "applications/APP-900-posting.md"), out)
    # section-by-heading repair on a file that has only some sections
    wr(root, "applications/APP-900.md", "# APP-900 : TestCo : AI Engineer\n\n- Status: Shortlisted\n- Date applied: \n\n## Contacts\n- me\n")
    rc, out = run(root, "new_company_file.py", "APP-900", "job.txt", "--force")
    t = rd(root, "applications/APP-900.md")
    check("company: adds only missing sections, keeps Contacts", rc == 0 and t.count("## Contacts") == 1 and "- me" in t and "## Learnings" in t and "## Outcome" in t, t)


def test_record(root):
    git(root, "init", "-q"); git(root, "checkout", "-q", "-b", "main")
    git(root, "-c", "user.name=t", "-c", "user.email=t@t", "add", "-A")
    git(root, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "base")
    ans = {"date": "2026-10-23", "via": "Company form", "answers": [["Name", "Jane Doe"], ["Pipe | test", "a | b"]],
           "cover_note": "Hello there.", "confirmation": "Thank you page shown"}
    wr(root, "ans.json", json.dumps(ans))
    # unrelated dirty file must not be committed
    wr(root, "applications/APP-001.md", rd(root, "applications/APP-001.md") + "\nlocal edit\n")
    before = {f: md5(root, f) for f in ("data/applications.json", "data/seen-jobs.csv", "applications/APP-900.md")}
    rc, out = run(root, "record_application.py", "APP-900", "ans.json", "--dry-run")
    check("record: dry-run writes nothing", rc == 0 and before == {f: md5(root, f) for f in before} and "would write" in out, out)
    rc, out = run(root, "record_application.py", "APP-999", "ans.json")
    check("record: unknown app refused", rc != 0 and "not in data" in out, out)
    bad = dict(ans, date="2026-13-45")
    wr(root, "bad.json", json.dumps(bad))
    rc, out = run(root, "record_application.py", "APP-900", "bad.json")
    check("record: invalid date refused, nothing written", rc != 0 and before == {f: md5(root, f) for f in before}, out)
    # missing detail file
    d = json.loads(rd(root, "data/applications.json"))
    app = next(a for a in d["apps"] if a["id"] == "APP-900")
    app["detail"] = "applications/NOPE.md"
    saved = rd(root, "data/applications.json")
    wr(root, "data/applications.json", json.dumps(d, indent=1, ensure_ascii=False) + "\n")
    rc, out = run(root, "record_application.py", "APP-900", "ans.json")
    check("record: missing detail file refused", rc != 0 and "does not exist" in out, out)
    wr(root, "data/applications.json", saved)
    # real record on a file whose template markers are missing: answers must not be dropped
    wr(root, "applications/APP-900.md", "# APP-900 : TestCo : AI Engineer\n\n- Status: Shortlisted\n- Date applied: \n")
    git(root, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-am", "setup", "--", "data", "applications/APP-900.md")
    rc, out = run(root, "record_application.py", "APP-900", "ans.json")
    t = rd(root, "applications/APP-900.md")
    d = json.loads(rd(root, "data/applications.json"))
    app = next(a for a in d["apps"] if a["id"] == "APP-900")
    row = next((r for r in ledger(root) if r["job_id"] == "9990001"), None)
    check("record: succeeds", rc == 0 and "committed" in out and "not pushed" in out, out)
    check("record: answers appended when markers missing", "## Submitted answers" in t and "| Name | Jane Doe |" in t and "Pipe \\| test" in t and "Hello there." in t, t)
    check("record: app fields + followUp +7 days", app["status"] == "Applied" and app["dateApplied"] == "2026-10-23" and app["followUp"]["nextCheck"] == "2026-10-30", str(app))
    check("record: ledger row set Applied with app_id", row is not None and row["status"] == "Applied" and row["app_id"] == "APP-900", str(row))
    last = git(root, "log", "-1", "--stat", "--format=%B")
    check("record: commit has Co-Authored-By", "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>" in last, last)
    check("record: only own files committed (unrelated edit left alone)", "APP-001.md" not in last and "APP-900.md" in last and "applications.json" in last, last)
    check("record: unrelated edit still uncommitted", "APP-001.md" in git(root, "status", "--short"))
    rc, out = run(root, "record_application.py", "APP-900", "ans.json")
    check("record: double-record refused", rc != 0 and "already Applied" in out, out)
    rc, out = run(root, "record_application.py", "APP-900", "ans.json", "--force", "--no-commit")
    check("record: --force allowed again", rc == 0, out)
    # template markers present -> rows inserted into the template table
    wr(root, "applications/APP-901.md", open(os.path.join(REPO, "templates", "applications", "TEMPLATE.md"), encoding="utf-8").read())
    d = json.loads(rd(root, "data/applications.json"))
    a2 = dict(app, id="APP-901", detail="applications/APP-901.md", status="Shortlisted", dateApplied="", link="https://x.test/jobs/1")
    d["apps"].append(a2)
    wr(root, "data/applications.json", json.dumps(d, indent=1, ensure_ascii=False) + "\n")
    rc, out = run(root, "record_application.py", "APP-901", "ans.json", "--no-commit")
    t = rd(root, "applications/APP-901.md")
    check("record: template table filled, cover note replaced", rc == 0 and "| Field | Answer |\n| --- | --- |\n| Name | Jane Doe |" in t
          and "## Cover note\nHello there." in t and t.count("## Submitted answers") == 1, t[:900])


def test_resumes(root):
    env = {}
    rc, out = run(root, "make_resumes.py", "--new", "APP-900", "--key", "testco", "--company", "Test Co", "--headline",
                  "AI Engineer | RAG", "--summary", "Engineer with over eight years of experience.", "--no-pdf")
    p = os.path.join(root, "applications/APP-900/Jane_Doe_TestCo_Resume.md")
    check("resumes: --new builds md at applications/<APP>/Jane_Doe_<Company>_Resume", rc == 0 and os.path.exists(p), out)
    t = open(p, encoding="utf-8").read() if os.path.exists(p) else ""
    check("resumes: contact block from applicant-details.md", "Testville, Testland | jane.doe@example.test | +46 701234567" in t and "linkedin.com/in/jane-doe-test | github.com/janedoe-test" in t and "Work authorization line." in t, t[:300])
    rc, out = run(root, "make_resumes.py", "--new", "APP-900", "--key", "bad", "--headline", "We leverage robust systems — fast",
                  "--summary", "Passionate about 35% gains.", "--no-pdf", "--out", "applications/APP-900/bad")
    check("resumes: warns on banned words, em dash and claims", rc == 0 and out.count("WARNING") >= 4 and "em dash" in out and "35%" in out and "leverage" in out, out)
    rc, out = run(root, "make_resumes.py", "base", "--no-pdf", "--out", "applications/APP-900/alt")
    check("resumes: --out override", rc == 0 and os.path.exists(os.path.join(root, "applications/APP-900/alt.md")), out)
    rc, out = run(root, "make_resumes.py", "base", "--out", "applications/APP-900/Jane_Doe_TestCo_Resume", env={"CHROME_PATH": "/nonexistent/chrome"})
    check("resumes: missing Chrome gives clear error", rc != 0 and "CHROME_PATH" in out, out)
    chrome = os.environ.get("CHROME_PATH") or "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    if os.path.exists(chrome):
        rc, out = run(root, "make_resumes.py", "base", "--out", "applications/APP-900/Jane_Doe_TestCo_Resume")
        pdf = os.path.join(root, "applications/APP-900/Jane_Doe_TestCo_Resume.pdf")
        check("resumes: PDF built, no page warning", rc == 0 and os.path.exists(pdf) and "pages" not in out, out)
    else:
        print("skip  resumes: Chrome not installed")


def test_board(root):
    rc, out = run(root, "build_board.py")
    h1, l1 = md5(root, "board/index.html"), md5(root, "applications-ledger.md")
    rc2, out2 = run(root, "build_board.py")
    check("board: builds and is deterministic", rc == 0 and rc2 == 0 and h1 == md5(root, "board/index.html") and l1 == md5(root, "applications-ledger.md"), out + out2)
    html = rd(root, "board/index.html")
    check("board: no Google Fonts fetch", "fonts.googleapis" not in html and "fonts.gstatic" not in html)
    check("board: tenant name and requirement shown", "Jane Doe" in html and "fixture pay" in html)
    led = rd(root, "applications-ledger.md")
    check("board: ledger md has no empty links", "]()" not in led and "Seen jobs" in led, "")
    # overdue marker: nextCheck in the past
    d = json.loads(rd(root, "data/applications.json"))
    app = next(a for a in d["apps"] if a["id"] == "APP-900")
    app["followUp"]["nextCheck"] = "2026-10-01"
    wr(root, "data/applications.json", json.dumps(d, indent=1, ensure_ascii=False) + "\n")
    run(root, "build_board.py")
    check("board: overdue follow-up computed", '"state": "overdue"' in rd(root, "board/index.html"))
    # unknown fit/track values do not crash
    app["fit"] = "weak"; app["track"] = "mystery_track"; app["detail"] = ""; app["resume"] = ""
    wr(root, "data/applications.json", json.dumps(d, indent=1, ensure_ascii=False) + "\n")
    rc, out = run(root, "build_board.py")
    check("board: unknown track and empty detail tolerated", rc == 0 and "]()" not in rd(root, "applications-ledger.md"), out)


def test_tenant(root):
    """Tenant resolution, isolation and leak detection, all in a scratch engine copy."""
    sys.path.insert(0, TOOLS)
    import importlib, tenant
    importlib.reload(tenant)
    eng = tempfile.mkdtemp(prefix="engine-test-", dir=os.environ.get("TEST_SCRATCH") or tempfile.gettempdir())
    for d in ("tools", "config", "templates", "tenants"):
        shutil.copytree(os.path.join(REPO, d), os.path.join(eng, d), ignore=shutil.ignore_patterns("__pycache__", ".active", "test_tools.py"))
    def tn(*a, env=None):
        e = {k: v for k, v in os.environ.items() if k not in ("JOBS_ROOT", "JOBS_TENANT")}
        e.update(env or {})
        p = subprocess.run([sys.executable, os.path.join(eng, "tools", "tenant.py"), *a], capture_output=True, text=True, env=e, cwd=eng)
        return p.returncode, p.stdout + p.stderr
    rc, out = tn("show")
    check("tenant: no tenant gives a plain setup message", rc != 0 and "setup" in out, out)
    rc, out = tn("create", "Ada Lovelace")
    check("tenant: create makes folder, fills name, activates", rc == 0 and os.path.isfile(os.path.join(eng, "tenants/ada-lovelace/tenant.json"))
          and "Ada Lovelace" in open(os.path.join(eng, "tenants/ada-lovelace/tenant.json")).read() and open(os.path.join(eng, "tenants/.active")).read().strip() == "ada-lovelace", out)
    rc, out = tn("create", "Ada Lovelace")
    check("tenant: duplicate name gets a new id, never overwrites", rc == 0 and os.path.isdir(os.path.join(eng, "tenants/ada-lovelace-2")), out)
    rc, out = tn("create", "Grace Hopper", "--id", "grace")
    check("tenant: second person is separate", rc == 0 and os.path.isdir(os.path.join(eng, "tenants/grace")), out)
    def tool(name, *a, env=None):
        e = {k: v for k, v in os.environ.items() if k not in ("JOBS_ROOT", "JOBS_TENANT")}
        e.update({"JOBS_TODAY": "2026-10-23", **(env or {})})
        p = subprocess.run([sys.executable, os.path.join(eng, "tools", name), *a], capture_output=True, text=True, env=e, cwd=eng)
        return p.returncode, p.stdout + p.stderr
    rc, out = tool("ledger_set.py", "5001", "--add", "--company", "OnlyAda", "--title", "AI Engineer", env={"JOBS_TENANT": "ada-lovelace"})
    ada = open(os.path.join(eng, "tenants/ada-lovelace/data/seen-jobs.csv")).read()
    grace = open(os.path.join(eng, "tenants/grace/data/seen-jobs.csv")).read()
    check("isolation: a row for one tenant never lands in another", rc == 0 and "OnlyAda" in ada and "OnlyAda" not in grace, out)
    rc, out = tool("build_board.py", env={"JOBS_TENANT": "grace"})
    check("isolation: each board is written into its own tenant folder", rc == 0 and os.path.isfile(os.path.join(eng, "tenants/grace/board/index.html"))
          and not os.path.exists(os.path.join(eng, "tenants/ada-lovelace/board/index.html")), out)
    check("isolation: board of one tenant shows only its own name", "Grace Hopper" in open(os.path.join(eng, "tenants/grace/board/index.html")).read()
          and "Ada Lovelace" not in open(os.path.join(eng, "tenants/grace/board/index.html")).read())
    rc, out = tool("check_consistency.py", env={"JOBS_TENANT": "grace"})
    check("consistency: fresh tenant passes", rc == 0, out)
    rc, out = tool("verify_tenant.py", env={"JOBS_TENANT": "grace"})
    check("verify: an empty new tenant is NOT READY and says what to ask", rc != 0 and "still empty" in out and "NOT READY" in out, out)
    rc, out = tool("ledger_set.py", "1", "--status", "New", env={"JOBS_ROOT": eng})
    check("isolation: JOBS_ROOT pointing at the engine is refused", rc != 0 and "engine" in out, out)
    # leak detection
    for tid, em in (("ada-lovelace", "ada@example.test"), ("grace", "grace@example.test")):
        p = os.path.join(eng, "tenants", tid, "tenant.json")
        m = json.loads(open(p).read()); m["email"] = em; m["phone"] = "+46 700 000 " + ("111" if tid == "grace" else "222")
        open(p, "w").write(json.dumps(m))
    rc, out = tool("check_leaks.py")
    check("leaks: clean tenants and engine report no leak", rc == 0, out)
    open(os.path.join(eng, "tenants/grace/candidate-profile.md"), "a").write("\nContact ada@example.test\n")
    rc, out = tool("check_leaks.py")
    check("leaks: another tenant's email inside a tenant is caught", rc != 0 and "another tenant" in out, out)
    open(os.path.join(eng, "tenants/grace/candidate-profile.md"), "w").write("clean\n")
    open(os.path.join(eng, "tools", "oops.py"), "w").write("# grace@example.test\n")
    rc, out = tool("check_leaks.py")
    check("leaks: a tenant email inside an engine file is caught", rc != 0 and "engine file" in out, out)
    shutil.rmtree(eng, ignore_errors=True)


def test_sync(root):
    """sync.py commits and pushes a tenant repo to a local bare remote; a tenant without a repo is skipped."""
    sys.path.insert(0, TOOLS)
    base = tempfile.mkdtemp(prefix="sync-test-", dir=os.environ.get("TEST_SCRATCH") or tempfile.gettempdir())
    bare = os.path.join(base, "remote.git"); work = os.path.join(base, "work")
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", bare], check=True)
    os.makedirs(work); git(work, "init", "-q", "-b", "main"); git(work, "remote", "add", "origin", bare)
    wr(work, "tenant.json", json.dumps({"name": "X", "git_name": "T", "git_email": "t@t.test"}))
    git(work, "-c", "user.name=t", "-c", "user.email=t@t", "add", "-A"); git(work, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "init")
    git(work, "push", "-q", "-u", "origin", "main")
    import importlib, sync
    importlib.reload(sync)
    wr(work, "data.txt", "x")
    msg = sync.sync("data", work, "Test sync", True)
    log = git(bare, "log", "--oneline", "main")
    check("sync: dirty tenant repo is committed and pushed", "pushed" in msg and "Test sync" in log, msg + log)
    msg = sync.sync("data", work, "Test sync", True)
    check("sync: clean repo reports nothing new", "pushed" not in msg and "up to date" in msg or "nothing" in msg, msg)
    plain = os.path.join(base, "plain"); os.makedirs(plain)
    check("sync: folder without its own repo is skipped, not pushed into a parent repo", "no git repo" in sync.sync("data", plain, "x", True))
    shutil.rmtree(base, ignore_errors=True)


def main():
    root = make_copy()
    print("testing on copy:", root)
    for fn in (test_ledger, test_company_file, test_record, test_resumes, test_board, test_tenant, test_sync):
        try:
            fn(root)
        except Exception as e:  # a crashing test is a failure, keep going
            FAILS.append(fn.__name__)
            print("FAIL ", fn.__name__, "crashed:", repr(e))
    print(f"\n{PASSES} passed, {len(FAILS)} failed")
    if not os.environ.get("TEST_KEEP"):
        shutil.rmtree(root, ignore_errors=True)
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
