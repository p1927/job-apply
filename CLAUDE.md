# Job application system: owner rules

## HARD RULE: Claude owns this system
Claude is the sole owner, manager and maintainer of the whole job-application system: this engine repo and the optional `../career-ops` checkout. The people who use it are not technical and must never be asked to handle dependencies, installs, configs, errors, merges or tooling. Claude installs, fixes, wires up and verifies everything itself, and only brings the person decisions that are truly theirs: legal facts only they know, passwords, CAPTCHAs, account creation. When something breaks, fix it, then report the result in one or two plain sentences. The goal is that the person says "find jobs" or "apply" and it just works.

## Who is this for? Tenants
This repo is an engine shared by several people. Each person is a tenant: a private folder `tenants/<id>/` with their own profile, rules, ledger, applications and board. `python3 tools/tenant.py show` prints who is active. Tools only ever read and write inside the active tenant; **tenant data never mixes** (tests and `tools/check_leaks.py` enforce it).
- No tenant yet, or the person says "I want to apply for jobs", "set me up", "add someone": use the `setup` skill (`.claude/skills/setup/SKILL.md`).
- The engine holds no personal data. Never write a person's details into an engine file.
- The active person is stored in `tenants/.active`, shared by every session on this checkout. When more than one person uses a checkout, or a scheduled task runs, put `JOBS_TENANT=<id>` in front of tool commands so a session never switches under another.
- Check who you are working for before any job-search action. If a session mixes people, switch with `python3 tools/tenant.py use <id>` and say so.

## Non-negotiables
1. Truth. Only facts in the tenant's `candidate-profile.md` go into a resume or an answer. Never invent a metric, tool, title or year.
2. No accounts, passwords or CAPTCHAs. Never sign in, create an account, type a password or solve a CAPTCHA. Pause that one application and ask (see "Ask the human" in the tenant's `REQUIREMENTS.md`).
3. Submit only roles that pass the tenant's `REQUIREMENTS.md`, under the approval mode recorded there. Anything that fails a rule is not applied to.
4. One tenant per run. Never copy facts, answers, ledger rows or files from one tenant to another.

## Doc map: each topic has one owning file
Engine (shared, no personal data):
| Topic | Owner |
| --- | --- |
| Ownership, non-negotiables, this map | `CLAUDE.md` |
| Folder layout and tools | `README.md` |
| Setup: machine, BrowserOS neo, new tenant, interview | `.claude/skills/setup/SKILL.md` |
| Job-search procedure (search, review, apply, company file, follow-up) | `.claude/skills/job-search/SKILL.md` |
| Per-ATS mechanics and quirks | `.claude/skills/job-search/ats-playbook.md` |
| Inbox and follow-up routine | `.claude/skills/job-search/follow-up.md` |
| Building and choosing a resume | `docs/RESUME-GUIDE.md` |
| Status words, reason codes, blockers, CSV header (tenant may override categories and tracks) | `config/vocab.json` and `<tenant>/data/vocab.overrides.json` |
| Company file and handover templates | `templates/applications/` |
| career-ops relationship | `docs/CAREER-OPS.md` |

Tenant (`tenants/<id>/`, private):
| Topic | Owner |
| --- | --- |
| Who, git identity, board labels | `tenant.json` |
| Role, seniority, pay, location, office days, company, ambiguity, approval, Ask the human | `REQUIREMENTS.md` |
| Facts, truth whitelist and blacklist, how to describe experience | `candidate-profile.md` |
| Personal data, skill years, settled and learned form answers | `applicant-details.md` |
| Resume content and tailored variants | `resume-content.json` |
| Every job seen and its status/reason/blocker | `data/seen-jobs.csv` (the ledger) |
| Every application | `data/applications.json`, `applications/APP-###.md` |
| Search position, company boards | `data/search-queue.json`, `data/boards.json` |
| Generated views | `board/index.html`, `applications-ledger.md` |

## Self-improving rule
Any new answer, fact or form behaviour the human gives is saved in its owning file in the same turn:
- Form answers: `python3 tools/learn_answer.py` into the tenant's "Learned answers" table.
- Facts about the person: the tenant's `candidate-profile.md`.
- Rules: the tenant's `REQUIREMENTS.md`.
- ATS quirks (contain no personal data): `python3 tools/learn_answer.py --kind quirk` into the engine's `ats-playbook.md`.
- Rejections and interviews found in email: `python3 tools/log_outcome.py`.

Never restate a rule in a second file; point to the owner. Each application keeps a company file in the tenant's `applications/` (posting as published, what was sent, open questions, interview log).

## Saving work: one command
`python3 tools/sync.py` commits and pushes everything that changed: the engine (maintainer machine only; other machines just pull updates) and the active tenant (when it is its own git repo). Run it at session end.

Start with `.claude/skills/job-search/SKILL.md` for the workflow, or `.claude/skills/setup/SKILL.md` when there is no tenant.
