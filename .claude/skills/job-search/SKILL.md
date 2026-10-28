---
name: job-search
description: Find, vet, rank and apply to jobs for the active person (tenant) using their own requirements, ledger and resume. Use for any job search, shortlist, resume tailoring, ledger, board, dashboard, follow-up or application task, so nobody has to repeat their requirements. If no person is set up yet, use the setup skill first.
---

# Job search procedure

Procedure only. Rules live elsewhere, one owner each. All file names below are inside the **active tenant folder** unless they start with `tools/`, `config/`, `docs/` or `.claude/` (engine).

## 0. Who is this for?
Run `python3 tools/tenant.py show`. If it says there is no tenant, stop and use the `setup` skill. Say which person you are working for in your first message. Never carry facts, answers or ledger rows over from another tenant.

Read before working (tenant files):
- `REQUIREMENTS.md`: role, pay, location, office days, approval mode, the "Ask the human" table, the ambiguity rule.
- `candidate-profile.md`: truth rules and how experience is worded. Nothing else decides what may be claimed.
- `applicant-details.md`: personal data, standard answers, "Learned answers".
Engine docs: `docs/RESUME-GUIDE.md` (resumes), `.claude/skills/job-search/ats-playbook.md` plus the tenant's `ats-quirks.md` if present (form mechanics), `config/vocab.json` plus `data/vocab.overrides.json` (the only allowed statuses, reason codes, blockers and categories).

## 1. Session start
0. Browser first. Run `python3 tools/setup_machine.py --fix` (opens BrowserOS neo if closed and checks its MCP port). If `mcp__browseros-neo__*` tools are not in this conversation, stop and follow Step 1.4 of the setup skill (new conversation) before searching or applying. Fallbacks that work without it and need no sign-in: Firecrawl (postings, pay research) and the Playwright plugin for company career pages and ATS forms (Teamtailor, Greenhouse, Lever, Ashby). Never use them for LinkedIn or anything behind a login.
1. `python3 tools/sync.py --pull` (updates the engine and the tenant repo; harmless if offline).
2. `python3 tools/check_consistency.py`. Fix every error before doing anything else.
3. Read `data/search-queue.json` and resume at the first entry that is not done.
4. Blockers: list ledger rows with a `blocker` set and applications waiting on the human. Ask for those first (section 5), then continue with other work.
5. Open the live dashboard for the person (section 10) unless it is already open, so they can watch the work.

## 2. Search
- Sources (use all that the tenant has): LinkedIn Jobs in BrowserOS neo; company career pages and boards (Greenhouse, Ashby, Lever) for known companies, and LinkedIn Jobs, both in BrowserOS neo, the way a person searches (filters, scrolling, paging). Firecrawl does not index LinkedIn; use it for career pages and pay research. `tools/search_boards.py` (uses `data/boards.json`) and career-ops portal scanning are optional cross-checks, never a replacement.
- Categories are the ones in the vocabulary (`python3 -c "import sys;sys.path.insert(0,'tools');import tenant;print(tenant.load_vocab()['categories'])"`). Every row gets exactly one. A search is not done until every category has been run; report empty ones with what you ran.
- Work through `data/search-queue.json`: each entry is one query x one page with a status (`pending`, `done`, `rate-limited`). Set it to in-progress when you start and done when its cards are all decided. Any agent can resume from it.
- Email is a source, not an afterthought. Every session reads the job-alert emails of the last 14 days (LinkedIn alerts "X is hiring", "New jobs similar to", saved-search digests, Glassdoor digests, Nordea and Volvo career-site notices). Email bodies are 80 to 120 KB each, so delegate it: one subagent reads Gmail (`get_thread` with `PLAIN_TEXT`), extracts `{source, email_date, linkedin_job_id, company, title, location}` per card from the `linkedin.com/comm/jobs/view/<id>/` links, and writes a JSON file in the scratchpad. Then run `python3 tools/coverage.py <file>.json --add --category <cat>`; every missing item becomes a `New` ledger row and is reviewed like any other card.
- LinkedIn is searched card by card, not from memory. Per queue entry: open the results URL in a new tab, run `tools/linkedin_harvest.js` as one `run` call (LinkedIn renders about 7 cards at a time, the script scrolls the container and returns every card as TSV), pipe the TSV into `python3 tools/coverage.py - --add --category <cat>`, then review the `New` rows. Job descriptions are not in the page text; the "Apply on company website" link carries the real ATS URL (see the playbook). Queries cover every role family in `REQUIREMENTS.md`: AI, ML, front end, full stack, forward deployed. The saved LinkedIn alerts are queries too; add them to the queue.
- Coverage is the score. After any harvest, `python3 tools/coverage.py --queue --report` shows how much of the queue ran and what the ledger holds. A job that appeared in an email or on a results page and is not in the ledger is a miss; the ledger also holds company-site ids (for example `tv4-8259879`), so the tool matches on company and title as well as id. Report the miss count per source at session end.
- Pace requests 2 to 3 seconds apart. At the first HTTP 429, stop, mark that queue entry `rate-limited`, and move to other work.
- Add new queries (keyword variants, company names with a location filter) to the queue instead of running them from memory.

## 3. Review loop (one job at a time)
1. Load the results page once. Scroll the results container until every card renders.
2. Ledger every card first: `python3 tools/ledger_set.py` with status `New`. Ids already decided are not reviewed again.
3. For each card in order: click it, read the detail pane in one call, decide against `REQUIREMENTS.md`, record the status at once, then take the next card. Do not reload between cards.
4. Every `Not-relevant` row needs a reason code from the vocabulary and a short note. A row without a reason is unfinished.
5. A `Relevant` role is applied (section 4) before the next page is reviewed. If it is blocked, set the blocker and go on.
5a. Rules change. After any change to `REQUIREMENTS.md` (front end and full stack were added late), re-open earlier rejections the new rule now allows: list `Not-relevant` rows with reason `swe-secondary` or `not-ai`, set the fitting ones back to `New` with a note, and review them. A row closed under an old rule is not a decision under the new one. Epidemic Sound, Spotify, Sinch and Ubiquiti came out of this.
5b. A person's explicit instruction beats a rule. When they say "apply there" to a role a rule closed (3 or 4 office days, not big tech, an earlier drop), apply, reopen the app record, and write the override with its date in the company file and the ledger note. Do not re-argue it.
5c. A role fails on substance, not on the title. Read the posting before applying: Swedbank "AI Engineer" was a Copilot Studio workshop role, WBD "Senior Software Engineer" was Kubernetes cluster operations. Say so and close it, unless the person asks to apply anyway.
6. Missing office days or pay does not block (ambiguity rule). Note it for the company file. A form that states the office days settles it: the application form is part of the posting (Aira's Teamtailor form asked "4 days in the office"; the ad said only "hybrid"). Read the form's screening questions before filling anything, and drop the role when they hit a stated hard fail.
7. Next page: step `start` by 25 until a page is short or repeats.

## 4. Apply
1. Apply on the company's own site, not LinkedIn Easy Apply, when both exist.
2. Choose the resume per `docs/RESUME-GUIDE.md`; build it if that role type has none yet (`tools/make_resumes.py`).
3. `python3 tools/new_company_file.py APP-0NN`, then paste the posting text into the posting file BEFORE applying. Postings get taken down.
4. Fill the form using `ats-playbook.md` and `applicant-details.md`. For every question not plainly in the standard answers, run `python3 tools/find_answer.py <several wordings>` first (it searches profile, details, learned answers, requirements and every earlier application's submitted answers). Read every field back before submitting. Never leave a section blank without saying so in the report.
5. Submit under the approval mode in `REQUIREMENTS.md`.
6. `python3 tools/record_application.py APP-0NN answers.json` (fills the company file, data, board, commit).
7. `python3 tools/ledger_set.py` to set the ledger row `Applied` with its `app_id`.

## 4a. Finding a posting and getting past forms
- LinkedIn gives no description and sometimes no apply link. Firecrawl search (`firecrawl_search` with the company and title) finds the company's own career page; for Google use `google.com/about/careers/applications/jobs/results/<id>`; a page that says "Job not found" is closed (ledger `Closed`).
- Open-ended essay questions (Teamtailor "how has AI changed how you work"): draft them from `candidate-profile.md` and the resume only, mark every gap [CHECK], show the draft to the person, then submit their corrected version. Professional experience only, no hobby projects, unless they say otherwise. Save each approved answer with `tools/learn_answer.py`.
- Email verification: Teamtailor and Oracle send a link or a six-digit code. Search Gmail for it (`newer_than:1h`, sender, `in:anywhere`); open links only on the employer's own domain. If the code never arrives (Sinch), say so once, request one new code, and ask the person to read it from their account; do not loop.
- Dropdowns that pick the wrong entry: Oracle Degree and Country comboboxes match the first hit ("India" gave British Indian Ocean Territory). Type, look at the options, click the exact one, read the value back. Never accept a wrong degree to get past a form: ask.

## 5. Human in the loop
- The cases and what to do are the "Ask the human" table in `REQUIREMENTS.md`. Never guess those facts, never sign in, never solve a CAPTCHA.
- Before any `fact` or `other` stop: (1) run `tools/find_answer.py` with at least three wordings; (2) answer from stored facts when they settle the question, even if the form words it differently ("permanent right to work" is settled by "Permanent resident of Sweden"); an earlier application that answered the same question counts. Ask only when the stored facts conflict with each other or say nothing. (3) When you do ask, say what you searched and give the exact question with its options.
- On a stop: set the ledger `blocker` (captcha, account, upload, fact, other), put the exact question or step in the company file under Open questions, tell the person once, and continue other work.
- On their reply: resume that one application. Save any new fact with `python3 tools/learn_answer.py` so they are never asked twice. Clear the blocker.

## 6. Self-improvement
After every application and every human answer, update the docs in place in the same turn:
- New form question and its answer: `tools/learn_answer.py` (lands in the tenant's `applicant-details.md`).
- New ATS behaviour or tool quirk: `python3 tools/learn_answer.py --kind quirk` (the shared `ats-playbook.md` on the maintainer's machine, else the tenant's own `ats-quirks.md`; read both, no personal data in quirks).
- New rule or correction from the person: the tenant's `REQUIREMENTS.md` (or `candidate-profile.md` for truth rules).
- Edit the existing text. Never add a changelog, dated log or restated rule to this skill.

## 7. Follow-up
Inbox and message routine is `follow-up.md` in this folder. Record rejections, interviews and offers with `python3 tools/log_outcome.py`; it updates the app status and the company file. Ledger status stays `Applied`.

## 8. Completion checklist
- [ ] Every card seen has a ledger row; no `New` rows left from this session. Email alerts of the last 14 days and every queue page run this session went through `tools/coverage.py` (misses added and reviewed); the queue shows what remains.
- [ ] Every `Not-relevant` row has a reason code.
- [ ] Every applied role has a company file, a saved posting, the resume path, and ledger `Applied` with `app_id`.
- [ ] Every blocker has a question recorded and has been reported.
- [ ] Search queue entries reflect what was run.
- [ ] New answers, quirks and rules went into their owner docs.
- [ ] Report: one table with a row per category (found, reviewed, relevant, applied, blocked), empty categories explained.

## 9. Session end
1. `python3 tools/check_consistency.py` (must pass).
2. `python3 tools/build_board.py`.
3. `python3 tools/sync.py` (commits and pushes the engine on the maintainer's machine and the tenant repo wherever it has one). Fix any failure yourself and report in one or two sentences.

## 10. The live dashboard
The person watches and browses their search in a read-only page that follows the files while you work. Start it with `python3 tools/dashboard.py` using `run_in_background`; with `JOBS_TENANT=<id>` in front when more than one person uses the checkout. It opens in their default browser, reuses a copy that is already running, and stops by itself about half a minute after the tab is closed. Say "I opened your dashboard" in one sentence; never explain the mechanics. Use it when they say "show the board", "dashboard", "what is happening", or at session start.
- It shows: overview and follow-ups, applications (board and list, each with its progress, requirement checks, company file, saved posting and the resume used), every job seen with the reason it was skipped, requirements, resumes and the profile. It reads `data/`, `applications/`, `REQUIREMENTS.md`, `candidate-profile.md`, `resume*` and `tenant.json`, so keep those files current (record applications and outcomes with the tools) and the page stays right without any extra step.
- The "Ask Claude" button in the corner just brings the Claude app forward; a few buttons (apply, change a requirement) also copy a request the person pastes. Such a message starts with `[From the job dashboard, <tenant id>; about APP-0NN ...]`. Treat it as a normal request from the person for that tenant, run `python3 tools/tenant.py use <id>` or `JOBS_TENANT` accordingly, and apply the usual rules (the "Ask Claude to apply" button changes nothing about the approval mode and the requirements check).
- The page is served only on `127.0.0.1`, serves only files inside the tenant folder, and never writes. If it fails to start, fix it yourself (`python3 tools/dashboard.py --no-open` prints the error) and report in one sentence. `python3 tools/build_board.py` still builds the static `board/index.html` and the ledger markdown for sharing.

## 11. LinkedIn profile upkeep (only on the person's request, approval before every edit)
Show the proposed headline, About and role text first; apply only after they approve. In BrowserOS neo the edit forms open at `/in/<id>/edit/intro/`, `/edit/forms/summary/new/`, `/details/experience/edit/forms/<id>/` (ids from the experience page links) and `/details/skills/edit/forms/new/`. The About and role description boxes are contenteditable or restrict `fill`: focus, select all, delete, then `insertText` line by line with Enter between lines, and read the text back. Open to Work titles are one free-text field in the "Edit Open to Work preferences" dialog. Skills can be added but pinning needs dragging; leave that to the person. Keep claims to `candidate-profile.md`; remove numbers the profile cannot back. After approval, update the profile file in the same turn.
