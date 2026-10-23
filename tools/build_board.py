#!/usr/bin/env python3
"""Generate board/index.html and applications-ledger.md from data/applications.json (+ data/seen-jobs.csv for counts).

data/applications.json is the single source of truth for applications. Edit it (or ask Claude to), then run:
    python3 tools/build_board.py
Open board/index.html in a browser. Links to resumes and detail files are relative, so keep the repo layout.
Writes into the active tenant folder only (tools/tenant.py). Env JOBS_TODAY=YYYY-MM-DD (fixed 'today' for tests). Output is deterministic.
"""
import csv, datetime, json, os, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tenant

ROOT = tenant.root()
META = tenant.tenant_meta(ROOT)
TODAY = os.environ.get("JOBS_TODAY") or str(datetime.date.today())
TRACK_LABELS = dict(META.get("track_labels") or {})   # tenant.json: {"track_key": "Label shown on the board"}
APP_DEFAULTS = {"company": "", "role": "", "track": "software", "location": "", "mode": "", "bigTech": False, "fit": "weak",
                "pay": "", "checks": [], "learn": [], "link": "", "links": [], "resume": "", "detail": "", "status": "Shortlisted",
                "dateFound": "", "dateApplied": "", "notes": "", "tag": "", "verdict": "check", "category": "Other", "blocker": ""}
FOLLOW_STATUSES = ("Applied", "Screening")


def atomic_write(p, text):
    d = os.path.dirname(p)
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tmp-", suffix=".part", dir=d)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        os.replace(tmp, p)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def load_json(rel, default=None):
    try:
        with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        if default is None:
            sys.exit(f"error: cannot read {rel}")
        return default


def add_days(day, n):
    try:
        return str(datetime.date.fromisoformat(day) + datetime.timedelta(days=n))
    except (ValueError, TypeError):
        return ""


def follow_up(a):
    """{'date','state'} for open applications: state is overdue, due or upcoming (from followUp.nextCheck)."""
    if a["status"] not in FOLLOW_STATUSES:
        return None
    fu = a.get("followUp") if isinstance(a.get("followUp"), dict) else {}
    day = fu.get("nextCheck") or add_days(a["dateApplied"], 7)
    if not day:
        return None
    return {"date": day, "state": "overdue" if day < TODAY else "due" if day == TODAY else "upcoming"}


def normalise(a):
    out = dict(APP_DEFAULTS)
    out.update({k: v for k, v in a.items() if v is not None})
    out["fu"] = follow_up(out)
    return out


def read_seen(vocab):
    """Ledger counts by status and the rows with a blocker. Returns {'ok': bool, ...}."""
    p = os.path.join(ROOT, "data/seen-jobs.csv")
    if not os.path.exists(p):
        return {"ok": False, "why": "data/seen-jobs.csv not found", "counts": {}, "total": 0, "needs": []}
    with open(p, encoding="utf-8", newline="") as f:
        rd = csv.DictReader(f)
        header = rd.fieldnames or []
        rows = list(rd)
    if "status" not in header:
        return {"ok": False, "why": "seen-jobs.csv has no status column", "counts": {}, "total": 0, "needs": []}
    counts, needs = {}, []
    for r in rows:
        st = (r.get("status") or "").strip() or "(none)"
        counts[st] = counts.get(st, 0) + 1
        if (r.get("blocker") or "").strip():
            needs.append({"kind": "ledger", "id": r.get("job_id", ""), "company": r.get("company", ""),
                          "title": r.get("title", ""), "blocker": r["blocker"].strip(), "app": r.get("app_id", "")})
    order = [s for s in vocab.get("ledger_status", []) if s in counts] + sorted(s for s in counts if s not in vocab.get("ledger_status", []))
    return {"ok": True, "why": "" if header == vocab.get("csv_header") else "header differs from vocab csv_header",
            "counts": {s: counts[s] for s in order}, "total": len(rows), "needs": needs}


def md_cell(x):
    return str(x if x is not None else "").replace("|", "\\|").replace("\n", " ").strip()


data = load_json("data/applications.json")
vocab = tenant.load_vocab(ROOT)
apps = [normalise(a) for a in data.get("apps", [])]
seen = read_seen(vocab)
app_order = list(vocab.get("app_status") or ["Shortlisted", "Applied", "Screening", "Interview", "Offer", "Rejected", "Withdrawn", "Dropped"])
app_order += [s for s in dict.fromkeys(a["status"] for a in apps) if s not in app_order]
track_keys = list(vocab.get("tracks") or TRACK_LABELS)
track_keys += [t for t in dict.fromkeys(a["track"] for a in apps) if t not in track_keys]
tracks = [[k, TRACK_LABELS.get(k, k)] for k in track_keys]
needs = seen["needs"] + [{"kind": "app", "id": a["id"], "company": a["company"], "title": a["role"], "blocker": a["blocker"], "app": a["id"]}
                         for a in apps if a["blocker"] and a["id"] not in {n["app"] for n in seen["needs"]}]
needs.sort(key=lambda x: (x["company"].lower(), x["id"]))
cnt = lambda s: sum(1 for a in apps if a["status"] == s)
board = dict(data)
board.update({"tenant": META.get("name", ""), "requirementLabels": META.get("requirement_labels") or {}, "apps": apps, "today": TODAY, "tracks": tracks, "appOrder": app_order, "seen": seen, "needs": needs,
              "fuOverdue": sum(1 for a in apps if a["fu"] and a["fu"]["state"] == "overdue"),
              "fuDue": sum(1 for a in apps if a["fu"] and a["fu"]["state"] == "due")})

# ---- ledger markdown (index) -------------------------------------------------
rows = ["# Applications Ledger", "",
        "Generated from `data/applications.json` by `tools/build_board.py`. Do not edit by hand. Open `board/index.html` for the full view.", "",
        f"Generated: {TODAY}", "",
        "Application status values: " + ", ".join(app_order), "",
        "Categories: " + ", ".join(f"{c} ({vocab['category_notes'][c]})" if c in vocab.get("category_notes", {}) else c for c in vocab["categories"]) + ".", ""]
if seen["ok"]:
    rows += ["Seen jobs (`data/seen-jobs.csv`, " + str(seen["total"]) + " rows): " + ", ".join(f"{k} {v}" for k, v in seen["counts"].items()), ""]
rows += ["| ID | Company | Category | Role | Date | URL | Location / Mode | Pay | Status | Detail |",
         "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
for a in sorted(apps, key=lambda x: x["id"]):
    detail = f"[{a['id']}]({a['detail']})" if a["detail"] else ""
    where = ", ".join(x for x in (a["location"], a["mode"]) if x)
    rows.append("| " + " | ".join(md_cell(x) for x in (a["id"], a["company"], a["category"], a["role"], a["dateApplied"] or a["dateFound"],
                                                           a["link"], where, a["pay"], a["status"])) + f" | {detail} |")
atomic_write(os.path.join(ROOT, "applications-ledger.md"), "\n".join(rows) + "\n")

# ---- board html --------------------------------------------------------------
TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Job Search Board</title>
<style>
/* Layout: a ruled ledger. One row per role, columns for place, pay, checks, status, links. Rows expand into the follow-up process. */
:root{
  --bg:#f2f5f3; --surface:#ffffff; --surface2:#e9efec; --ink:#14201b; --muted:#566860; --line:#d3dcd7;
  --accent:#1d6b52; --accent-ink:#ffffff; --accent-weak:#d9ebe3;
  --ok:#1b7a45; --ok-bg:#dcf0e3; --warn:#8a5a00; --warn-bg:#f7ebcc; --bad:#b3261e; --bad-bg:#f8dcd9; --unk:#566860; --unk-bg:#e4eae7;
  --sans:system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif; --mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){
  --bg:#0d1411; --surface:#141e19; --surface2:#1b2822; --ink:#e5eee9; --muted:#9aaca3; --line:#2a3a33;
  --accent:#58c4a0; --accent-ink:#06221a; --accent-weak:#1c3a30;
  --ok:#6fd49a; --ok-bg:#16301f; --warn:#e5b94e; --warn-bg:#352a0e; --bad:#ff8f86; --bad-bg:#3b1815; --unk:#9aaca3; --unk-bg:#1f2c26; color-scheme:dark}}
:root[data-theme="dark"]{
  --bg:#0d1411; --surface:#141e19; --surface2:#1b2822; --ink:#e5eee9; --muted:#9aaca3; --line:#2a3a33;
  --accent:#58c4a0; --accent-ink:#06221a; --accent-weak:#1c3a30;
  --ok:#6fd49a; --ok-bg:#16301f; --warn:#e5b94e; --warn-bg:#352a0e; --bad:#ff8f86; --bad-bg:#3b1815; --unk:#9aaca3; --unk-bg:#1f2c26; color-scheme:dark}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);font-size:15px;line-height:1.45;
  padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));padding-block:20px 56px}
.wrap{max-width:1240px;margin:0 auto}
a{color:var(--accent);text-underline-offset:3px}
a:focus-visible,button:focus-visible,input:focus-visible,select:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
header.top{display:flex;flex-wrap:wrap;gap:12px 24px;align-items:flex-end;justify-content:space-between;padding-bottom:16px;border-bottom:2px solid var(--ink)}
h1{margin:0;font-size:clamp(26px,4vw,38px);line-height:1.05;letter-spacing:-.02em;text-wrap:balance}
.sub{margin:6px 0 0;color:var(--muted);font-size:14px}
.tools{display:flex;gap:8px;flex-wrap:wrap}
.btn{font:inherit;font-size:13px;font-weight:500;border:1px solid var(--line);background:var(--surface);color:var(--ink);padding:7px 12px;border-radius:6px;cursor:pointer;text-decoration:none;display:inline-flex;gap:6px;align-items:center}
.btn:hover{border-color:var(--accent)}
.pipe{display:grid;grid-template-columns:repeat(auto-fit,minmax(104px,1fr));margin:18px 0 0;border:1px solid var(--line);background:var(--surface)}
.pipe button{font:inherit;text-align:left;border:0;border-right:1px solid var(--line);background:transparent;color:var(--ink);padding:10px 12px;cursor:pointer}
.pipe button:last-child{border-right:0}
.pipe button[aria-pressed="true"]{background:var(--accent);color:var(--accent-ink)}
.pipe .n{display:block;font-family:var(--mono);font-size:24px;font-weight:500;line-height:1.1}
.pipe .l{font-size:12px;letter-spacing:.04em;text-transform:uppercase}
.strip{margin:18px 0 0;border:1px solid var(--line);background:var(--surface);padding:10px 14px}
.strip h3{margin:0 0 6px;font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
.strip .stats{display:flex;flex-wrap:wrap;gap:6px 18px;font-size:14px}
.strip .stats b{font-family:var(--mono);font-weight:500}
.strip ul{margin:4px 0 0;padding-left:18px;font-size:14px}
.fu{display:inline-block;font-size:11px;font-weight:700;border-radius:4px;padding:1px 6px;margin:5px 5px 0 0}
.fu.overdue{background:var(--bad-bg);color:var(--bad)}.fu.due{background:var(--warn-bg);color:var(--warn)}
details.req{margin:16px 0 0;border:1px solid var(--line);background:var(--surface)}
details.req summary{cursor:pointer;padding:10px 14px;font-weight:600;list-style:none}
details.req summary::-webkit-details-marker{display:none}
details.req summary::after{content:"Show";float:right;font-weight:500;color:var(--muted);font-size:13px}
details.req[open] summary::after{content:"Hide"}
.reqgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:0;border-top:1px solid var(--line)}
.reqgrid div{padding:10px 14px;border-right:1px solid var(--line);border-bottom:1px solid var(--line);min-width:0}
.reqgrid dt{font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
.reqgrid dd{margin:2px 0 0;font-weight:500}
.filters{display:flex;flex-wrap:wrap;gap:10px 14px;align-items:center;margin:18px 0 6px}
.filters label{font-size:12px;letter-spacing:.05em;text-transform:uppercase;color:var(--muted);display:flex;gap:6px;align-items:center}
select,input[type=search]{font:inherit;font-size:14px;color:var(--ink);background:var(--surface);border:1px solid var(--line);border-radius:6px;padding:6px 9px;min-width:0}
input[type=search]{width:min(240px,100%)}
.count{margin-left:auto;font-family:var(--mono);font-size:13px;color:var(--muted)}
h2.group{margin:26px 0 8px;font-size:13px;letter-spacing:.07em;text-transform:uppercase;display:flex;gap:10px;align-items:baseline}
h2.group span{font-family:var(--mono);font-weight:400;color:var(--muted)}
.head,.row{display:grid;grid-template-columns:minmax(0,2.2fr) minmax(0,1.3fr) minmax(0,1.9fr) minmax(0,1.5fr) minmax(0,1.1fr) minmax(0,1.3fr);gap:14px;padding:12px 14px;align-items:start}
.head{font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);border-bottom:1px solid var(--ink);padding-block:6px}
.card{border-bottom:1px solid var(--line);background:var(--surface)}
.card:first-of-type{border-top:0}
.card.dropped{opacity:.6}
.co{font-weight:700;font-size:16px;overflow-wrap:anywhere}
.role{color:var(--muted);font-size:14px;overflow-wrap:anywhere}
.tag{display:inline-block;font-size:11px;font-weight:600;border:1px solid var(--line);border-radius:4px;padding:1px 6px;margin:5px 5px 0 0;color:var(--muted)}
.tag.big{border-color:var(--accent);color:var(--accent)}
.where small,.pay small{display:block;color:var(--muted);font-size:13px}
.pay .p{font-size:13px;overflow-wrap:anywhere}
.chips{display:flex;flex-wrap:wrap;gap:4px}
.chk{font-size:12px;font-weight:600;padding:2px 7px;border-radius:4px;display:inline-flex;gap:4px;align-items:center;cursor:help}
.chk::before{font-family:var(--mono);font-weight:500}
.chk.pass{background:var(--ok-bg);color:var(--ok)}.chk.pass::before{content:"+"}
.chk.warn{background:var(--warn-bg);color:var(--warn)}.chk.warn::before{content:"~"}
.chk.fail{background:var(--bad-bg);color:var(--bad)}.chk.fail::before{content:"x"}
.chk.unknown{background:var(--unk-bg);color:var(--unk)}.chk.unknown::before{content:"?"}
.fit{font-size:13px;font-weight:600;text-transform:capitalize;margin-bottom:5px}
.pill{display:inline-block;font-size:12px;font-weight:600;padding:2px 9px;border-radius:99px;background:var(--surface2);border:1px solid var(--line)}
.pill.Applied,.pill.Screening,.pill.Interview,.pill.Offer{background:var(--accent);color:var(--accent-ink);border-color:var(--accent)}
.pill.Dropped,.pill.Rejected,.pill.Withdrawn{background:var(--bad-bg);color:var(--bad);border-color:transparent}
.links{display:flex;flex-direction:column;gap:3px;font-size:14px}
.links a{overflow-wrap:anywhere}
.more{font:inherit;font-size:13px;border:0;background:none;color:var(--accent);cursor:pointer;padding:0;margin-top:8px;text-align:left}
.panel{padding:4px 14px 18px;display:grid;grid-template-columns:minmax(0,1.5fr) minmax(0,1fr);gap:20px;border-top:1px dashed var(--line);background:var(--surface)}
.panel h3{margin:12px 0 6px;font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
ol.steps{list-style:none;margin:0;padding:0;counter-reset:s}
ol.steps li{display:grid;grid-template-columns:22px minmax(0,1fr);gap:8px;padding:5px 0;border-bottom:1px solid var(--line);font-size:14px}
ol.steps li::before{counter-increment:s;content:counter(s);font-family:var(--mono);font-size:12px;color:var(--muted);text-align:right;padding-top:2px}
ol.steps li.done{color:var(--muted)}
ol.steps li.done b{text-decoration:line-through;font-weight:500}
ol.steps li.now{background:var(--accent-weak);margin:0 -6px;padding:5px 6px;border-radius:4px;border-bottom-color:transparent}
ol.steps small{display:block;color:var(--muted)}
ul.plain{margin:0;padding-left:18px}ul.plain li{margin:2px 0;font-size:14px}
.notes{font-size:14px;margin:0}
.kv{display:grid;grid-template-columns:auto 1fr;gap:3px 12px;font-size:13px;margin:0}.kv dt{color:var(--muted)}.kv dd{margin:0;font-family:var(--mono);font-size:12.5px}
.left{margin-top:30px}
.left table{width:100%;border-collapse:collapse;font-size:14px}
.left th{text-align:left;font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);border-bottom:1px solid var(--ink);padding:6px 10px 6px 0}
.left td{padding:8px 10px 8px 0;border-bottom:1px solid var(--line);vertical-align:top;overflow-wrap:anywhere}
.scroll{overflow-x:auto}
.empty{padding:28px 14px;color:var(--muted);background:var(--surface);border-bottom:1px solid var(--line)}
footer{margin-top:28px;color:var(--muted);font-size:13px}
@media (max-width:980px){
  .head{display:none}
  .row{grid-template-columns:1fr 1fr;gap:10px 14px}
  .row>.c1{grid-column:1/-1}
  .panel{grid-template-columns:1fr}
}
@media (max-width:520px){.row{grid-template-columns:1fr}}
@media (prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}
</style>
</head>
<body>
<div class="wrap">
<header class="top">
  <div>
    <h1 id="ttl">Job Search Board</h1>
    <p class="sub" id="sub"></p>
  </div>
  <div class="tools">
    <a class="btn" id="gh" target="_blank" rel="noopener">Repo</a>
    <a class="btn" id="gp" target="_blank" rel="noopener">GitHub Project</a>
    <button class="btn" id="theme" type="button">Theme: system</button>
  </div>
</header>

<section class="strip" id="strip" aria-label="Summary"></section>

<div class="pipe" id="pipe" role="group" aria-label="Filter by status"></div>

<details class="req" open>
  <summary>What I am looking for</summary>
  <dl class="reqgrid" id="req"></dl>
</details>

<div class="filters">
  <label for="fTrack">Track
    <select id="fTrack"><option value="">All</option></select></label>
  <label for="fVerdict">Requirements
    <select id="fVerdict"><option value="">All</option><option value="pass">All checks pass</option><option value="check">Some checks open</option><option value="fail">A check fails</option></select></label>
  <label for="fQ">Search <input id="fQ" type="search" placeholder="Company or role"></label>
  <span class="count" id="count"></span>
</div>

<main id="list"></main>

<section class="left" aria-labelledby="lh">
  <h2 class="group" id="lh">Left out <span id="leftN"></span></h2>
  <div class="scroll"><table><thead><tr><th>Company</th><th>Role</th><th>Why</th></tr></thead><tbody id="leftBody"></tbody></table></div>
</section>
<footer>Generated from data/applications.json by tools/build_board.py. Links to resumes and detail files are relative to this folder. Pay figures are estimates unless the posting prints a range.</footer>
</div>

<script>
const D = __DATA__;
const STEPS = [
  {t:'Found and checked against your requirements', w:'Claude'},
  {t:'Tailored resume built', w:'Claude'},
  {t:'You review and say yes', w:'You'},
  {t:'Application submitted', w:'Claude, only after your yes'},
  {t:'Confirmation and every answer saved in the application file', w:'Claude'},
  {t:'Follow-up check at day 7', w:'Claude checks status; any message to a recruiter needs your OK'},
  {t:'Recruiter screen', w:'You'},
  {t:'Interviews', w:'You, Claude helps you prepare'},
  {t:'Offer or rejection', w:'Negotiate toward the target pay in the requirements'}
];
const DONE_BY_STATUS = {Shortlisted:2, Ready:2, Applied:5, Screening:7, Interview:8, Offer:9, Rejected:9, Withdrawn:9, Dropped:2};
const ORDER = D.appOrder;
const TRACKS = D.tracks;
const VR = {pass:0, check:1, fail:2}, FR = {strong:0, good:1, stretch:2, weak:3};
const rank = (m, k) => (k in m ? m[k] : 9);
const $ = s => document.querySelector(s);
const el = (t, c, h) => { const e = document.createElement(t); if (c) e.className = c; if (h != null) e.innerHTML = h; return e; };
const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const state = {status:'', track:'', verdict:'', q:'', open:{}};

$('#gh').href = D.repo; $('#gp').href = D.projectBoard;
if (D.tenant) { $('#ttl').textContent = 'Job Search Board: ' + D.tenant; document.title = 'Job Search Board: ' + D.tenant; }
$('#gh').hidden = !D.repo; $('#gp').hidden = !D.projectBoard;
$('#sub').textContent = 'Updated ' + D.today + '. Standing approval applies to roles that pass the rules; everything is reported afterwards.';
$('#fTrack').innerHTML += TRACKS.map(t => '<option value="' + esc(t[0]) + '">' + esc(t[1]) + '</option>').join('');

const reqLabels = Object.keys(D.requirementLabels || {}).length ? D.requirementLabels : {pay:'Pay', role:'Role', mode:'Mode', office:'Office days', location:'Location', learning:'Learning'};
$('#req').innerHTML = Object.keys(reqLabels).filter(k => D.requirements && D.requirements[k]).map(k => '<div><dt>' + reqLabels[k] + '</dt><dd>' + esc(D.requirements[k]) + '</dd></div>').join('');

function buildStrip(){
  const n = s => D.apps.filter(a => a.status === s).length, S = D.seen;
  let h = '<h3>Applications</h3><div class="stats">' + ['Applied','Screening','Interview','Offer','Rejected'].map(s => s + ' <b>' + n(s) + '</b>').join('') + '</div>';
  h += '<div class="stats">Follow-ups overdue <b>' + D.fuOverdue + '</b> Follow-ups due today <b>' + D.fuDue + '</b></div>';
  h += '<h3 style="margin-top:10px">Seen jobs' + (S.ok ? ' (' + S.total + ')' : '') + '</h3>';
  h += S.ok ? '<div class="stats">' + Object.keys(S.counts).map(k => esc(k) + ' <b>' + S.counts[k] + '</b>').join('') + '</div>' : '<div class="stats">Not available: ' + esc(S.why) + '</div>';
  h += '<h3 style="margin-top:10px">Needs you (' + D.needs.length + ')</h3>';
  h += D.needs.length ? '<ul>' + D.needs.map(x => '<li><b>' + esc(x.company) + '</b> ' + esc(x.title) + ' <span class="tag">' + esc(x.blocker) + '</span><span class="tag">' + esc(x.kind === 'app' ? x.id : x.id + (x.app ? ' / ' + x.app : '')) + '</span></li>').join('') + '</ul>' : '<div class="stats">Nothing is waiting on you</div>';
  $('#strip').innerHTML = h;
}
function buildPipe(){
  const box = $('#pipe'); box.innerHTML = '';
  const all = el('button', '', '<span class="n">' + D.apps.length + '</span><span class="l">All</span>');
  all.type = 'button'; all.setAttribute('aria-pressed', state.status === ''); all.onclick = () => {state.status = ''; render();};
  box.appendChild(all);
  ORDER.forEach(s => {
    const n = D.apps.filter(a => a.status === s).length;
    const b = el('button', '', '<span class="n">' + n + '</span><span class="l">' + s + '</span>');
    b.type = 'button'; b.setAttribute('aria-pressed', state.status === s);
    b.onclick = () => {state.status = state.status === s ? '' : s; render();};
    box.appendChild(b);
  });
}
function link(href, text, ext){ return '<a href="' + esc(href) + '"' + (ext ? ' target="_blank" rel="noopener"' : '') + '>' + text + '</a>'; }
function followDate(a){ return a.fu ? a.fu.date : ''; }
function card(a){
  const c = el('article', 'card' + (a.status === 'Dropped' ? ' dropped' : ''));
  const chips = a.checks.map(k => '<span class="chk ' + k.s + '" title="' + esc(k.k + ': ' + k.n) + '" aria-label="' + esc(k.k + ' ' + k.s + ': ' + k.n) + '">' + k.k + '</span>').join('');
  const payBad = a.checks.find(k => k.k === 'Pay');
  const links = (a.link ? [link(a.link, 'Job posting', true)] : [])
    .concat((a.links || []).map(x => link(x[1], esc(x[0]), true)))
    .concat(a.resume ? [link('../' + a.resume, 'Resume (PDF)')] : []).concat(a.detail ? [link('../' + a.detail, 'Application file')] : []);
  const row = el('div', 'row');
  row.innerHTML =
    '<div class="c1"><div class="co">' + esc(a.company) + '</div><div class="role">' + esc(a.role) + '</div>' +
      (a.bigTech ? '<span class="tag big">Big tech</span>' : '') + (a.tag ? '<span class="tag">' + esc(a.tag) + '</span>' : '') + '<span class="tag">' + esc(a.id) + '</span></div>' +
    '<div class="where">' + esc(a.location) + '<small>' + esc(a.mode) + '</small></div>' +
    '<div class="pay"><div class="p">' + esc(a.pay) + '</div><small>' + esc(payBad ? payBad.n : '') + '</small></div>' +
    '<div class="chips">' + chips + '</div>' +
    '<div><div class="fit">' + esc(a.fit) + ' fit</div><span class="pill ' + esc(a.status) + '">' + esc(a.status) + '</span>' +
      (a.fu && a.fu.state !== 'upcoming' ? '<br><span class="fu ' + a.fu.state + '">Follow-up ' + (a.fu.state === 'overdue' ? 'overdue since ' : 'due ') + esc(a.fu.date) + '</span>' : '') +
      (a.blocker ? '<br><span class="tag">Needs you: ' + esc(a.blocker) + '</span>' : '') + '</div>' +
    '<div class="links">' + links.join('') + '</div>';
  c.appendChild(row);
  const btn = el('button', 'more', state.open[a.id] ? 'Hide process and notes' : 'Show process, things to learn and notes');
  btn.type = 'button'; btn.setAttribute('aria-expanded', !!state.open[a.id]);
  btn.style.margin = '0 14px 12px';
  btn.onclick = () => {state.open[a.id] = !state.open[a.id]; render();};
  c.appendChild(btn);
  if (state.open[a.id]) {
    const done = DONE_BY_STATUS[a.status] || 0, fu = followDate(a);
    const steps = STEPS.map((s, i) => '<li class="' + (i < done ? 'done' : i === done ? 'now' : '') + '"><div><b>' + esc(s.t) + '</b><small>' + esc(s.w) + (i === 5 && fu ? ' (due ' + fu + ')' : '') + '</small></div></li>').join('');
    const notes = a.checks.map(k => '<li><b>' + k.k + ':</b> ' + esc(k.n) + '</li>').join('');
    const learn = (a.learn || []).map(x => '<li>' + esc(x) + '</li>').join('') || '<li>Nothing flagged</li>';
    const p = el('div', 'panel');
    p.innerHTML = '<div><h3>Follow-up process</h3><ol class="steps">' + steps + '</ol></div>' +
      '<div><h3>Things to learn along the way</h3><ul class="plain">' + learn + '</ul>' +
      '<h3>Requirement checks</h3><ul class="plain">' + notes + '</ul>' +
      '<h3>Notes</h3><p class="notes">' + esc(a.notes) + '</p>' +
      '<h3>Dates</h3><dl class="kv"><dt>Found</dt><dd>' + esc(a.dateFound) + '</dd><dt>Applied</dt><dd>' + esc(a.dateApplied || 'not yet') + '</dd><dt>Follow-up</dt><dd>' + esc(fu || 'after applying') + '</dd></dl></div>';
    c.appendChild(p);
  }
  return c;
}
function render(){
  buildStrip();
  buildPipe();
  $('#fTrack').value = state.track; $('#fVerdict').value = state.verdict;
  const q = state.q.toLowerCase();
  const list = D.apps.filter(a =>
    (!state.status || a.status === state.status) && (!state.track || a.track === state.track) &&
    (!state.verdict || a.verdict === state.verdict) && (!q || (a.company + ' ' + a.role).toLowerCase().includes(q)));
  $('#count').textContent = list.length + ' of ' + D.apps.length + ' roles';
  const out = $('#list'); out.innerHTML = '';
  if (!list.length) out.appendChild(el('div', 'empty', 'No roles match these filters.'));
  TRACKS.forEach(([key, name]) => {
    const items = list.filter(a => a.track === key).sort((x, y) =>
      (x.status === 'Dropped') - (y.status === 'Dropped') || rank(VR, x.verdict) - rank(VR, y.verdict) || rank(FR, x.fit) - rank(FR, y.fit));
    if (!items.length) return;
    out.appendChild(el('h2', 'group', esc(name) + ' <span>' + items.length + '</span>'));
    out.appendChild(el('div', 'head', '<div>Company and role</div><div>Where</div><div>Pay</div><div>Checks</div><div>Fit and status</div><div>Links</div>'));
    items.forEach(a => out.appendChild(card(a)));
  });
}
$('#fTrack').onchange = e => {state.track = e.target.value; render();};
$('#fVerdict').onchange = e => {state.verdict = e.target.value; render();};
$('#fQ').oninput = e => {state.q = e.target.value; render();};

$('#leftN').textContent = (D.left || []).length;
$('#leftBody').innerHTML = (D.left || []).map(x => '<tr><td>' + (x.link ? link(x.link, esc(x.company), true) : esc(x.company)) + '</td><td>' + esc(x.role) + '</td><td>' + esc(x.why) + '</td></tr>').join('');

(function theme(){
  const modes = ['system','light','dark']; let i = 0;
  try { const s = localStorage.getItem('jb-theme'); if (s && modes.includes(s)) i = modes.indexOf(s); } catch(e) {}
  const apply = () => {
    const m = modes[i], r = document.documentElement;
    if (m === 'system') r.removeAttribute('data-theme'); else r.setAttribute('data-theme', m);
    $('#theme').textContent = 'Theme: ' + m;
    try { localStorage.setItem('jb-theme', m); } catch(e) {}
  };
  $('#theme').onclick = () => {i = (i + 1) % 3; apply();};
  apply();
})();
render();
</script>
</body>
</html>
"""
html = TEMPLATE.replace("__DATA__", json.dumps(board, ensure_ascii=False).replace("</", "<\\/"))
atomic_write(os.path.join(ROOT, "board/index.html"), html)
print("wrote board/index.html and applications-ledger.md")
