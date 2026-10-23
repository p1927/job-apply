---
name: job-search
description: Find, vet, rank and apply to jobs for the active person (tenant) using their own requirements, ledger and resume. Use for any job search, shortlist, resume tailoring, ledger, board, follow-up or application task, so nobody has to repeat their requirements. If no person is set up yet, use the setup skill first.
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
1. `python3 tools/sync.py --pull` (updates the engine and the tenant repo; harmless if offline).
2. `python3 tools/check_consistency.py`. Fix every error before doing anything else.
3. Read `data/search-queue.json` and resume at the first entry that is not done.
4. Blockers: list ledger rows with a `blocker` set and applications waiting on the human. Ask for those first (section 5), then continue with other work.

## 2. Search
- Sources (use all that the tenant has): LinkedIn Jobs in BrowserOS neo; company career pages and boards (Greenhouse, Ashby, Lever) for known companies, and LinkedIn Jobs, both in BrowserOS neo, the way a person searches (filters, scrolling, paging). Firecrawl does not index LinkedIn; use it for career pages and pay research. `tools/search_boards.py` (uses `data/boards.json`) and career-ops portal scanning are optional cross-checks, never a replacement.
- Categories are the ones in the vocabulary (`python3 -c "import sys;sys.path.insert(0,'tools');import tenant;print(tenant.load_vocab()['categories'])"`). Every row gets exactly one. A search is not done until every category has been run; report empty ones with what you ran.
- Work through `data/search-queue.json`: each entry is one query x one page with a status (`pending`, `done`, `rate-limited`). Set it to in-progress when you start and done when its cards are all decided. Any agent can resume from it.
- Pace requests 2 to 3 seconds apart. At the first HTTP 429, stop, mark that queue entry `rate-limited`, and move to other work.
- Add new queries (keyword variants, company names with a location filter) to the queue instead of running them from memory.

## 3. Review loop (one job at a time)
1. Load the results page once. Scroll the results container until every card renders.
2. Ledger every card first: `python3 tools/ledger_set.py` with status `New`. Ids already decided are not reviewed again.
3. For each card in order: click it, read the detail pane in one call, decide against `REQUIREMENTS.md`, record the status at once, then take the next card. Do not reload between cards.
4. Every `Not-relevant` row needs a reason code from the vocabulary and a short note. A row without a reason is unfinished.
5. A `Relevant` role is applied (section 4) before the next page is reviewed. If it is blocked, set the blocker and go on.
6. Missing office days or pay does not block (ambiguity rule). Note it for the company file.
7. Next page: step `start` by 25 until a page is short or repeats.

## 4. Apply
1. Apply on the company's own site, not LinkedIn Easy Apply, when both exist.
2. Choose the resume per `docs/RESUME-GUIDE.md`; build it if that role type has none yet (`tools/make_resumes.py`).
3. `python3 tools/new_company_file.py APP-0NN`, then paste the posting text into the posting file BEFORE applying. Postings get taken down.
4. Fill the form using `ats-playbook.md` and `applicant-details.md`. Read every field back before submitting. Never leave a section blank without saying so in the report.
5. Submit under the approval mode in `REQUIREMENTS.md`.
6. `python3 tools/record_application.py APP-0NN answers.json` (fills the company file, data, board, commit).
7. `python3 tools/ledger_set.py` to set the ledger row `Applied` with its `app_id`.

## 5. Human in the loop
- The cases and what to do are the "Ask the human" table in `REQUIREMENTS.md`. Never guess those facts, never sign in, never solve a CAPTCHA.
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
- [ ] Every card seen has a ledger row; no `New` rows left from this session.
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
