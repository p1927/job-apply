# Upstream survey: what other job-search repos do that we do not

Date: 2026-10-29. Method: read-only. Five agents read the READMEs, docs and code headers of the repos below. Nothing was run or installed. Details they did not read line by line (edge cases) are unverified. Star counts are from search results on the same date.

Full per-repo reports (feature tables with file names) are in `docs/upstream-survey/`:
[career-ops](upstream-survey/career-ops.md) · [jobsync and job-ops](upstream-survey/jobsync-jobops.md) · [JobSpy and jobhive](upstream-survey/jobspy-jobhive.md) · [boards and gigs](upstream-survey/boards-gigs.md) · [AIHawk](upstream-survey/aihawk.md)

## The repos

| Repo | Stars | Licence | Verdict |
|---|---|---|---|
| career-ops (career-ops-hq) | ~78K | MIT | Best source of ideas and providers. Port logic to Python, pin its commit, do not run its Node code. Keep attribution (offer-prep is adapted from Apache-2.0 text). |
| JobSync (Gsync) | 1.5K | MIT | Safe to adapt: fit-score convention, pre-rank funnel, company slug list. |
| job-ops (DaKheera47) | 4.1K | AGPL-3.0 + Commons Clause | Ideas only. Copying code or prompts into our MIT repo would breach the licence. |
| JobSpy (speedyapply) | 4.6K | MIT | Mostly ToS-risky boards (LinkedIn, Indeed, Glassdoor) and hardcoded keys. At most an optional Naukri-only adapter. Needs Python 3.10+. |
| ats-scrapers "jobhive" (kalil0321) | ~190 | MIT | Reuse its company lists to grow `boards.json`; write our own small fetchers. Beta, one maintainer, hosted dataset has no stated terms. |
| awesome-job-boards (emredurukn) | 1.1K | n/a | Source ideas; India section is thin. |
| AIHawk (feder-cr) | ~31K | AGPL | Upstream is no longer a job tool. Old fork read for form-filling lessons only. Do not use. |
| Auto_job_applier_linkedIn (GodsScion) | 3K | MIT | LinkedIn bot, ban risk. README ideas only (dry-run mode). |
| Levergreen | 47 | MIT | Skip. |

Never adopt: any LinkedIn, Indeed or Glassdoor bot or scraper (account-ban and ToS risk), anything that hides automation or invents experience, any Upwork scraper or auto-bidder (all need a login; Upwork removed RSS on 2024-08-20).

## Gaps in our engine, ranked by value for effort

Effort: S small, M medium, L large. Each line is a backlog candidate (no project backlog was found, so they are listed here).

### Do first (cheap, high value)
1. **Fix `contract` reason code** (S). `config/vocab.json` treats contract as a rejection reason, so contract gigs would be auto-dropped. Needs a per-tenant override or a gig track. Blocks everything about gigs.
2. **Free job feeds** (S each). Verified keyless on 2026-10-29: RemoteOK `/api`, We Work Remotely RSS, Remotive `/api/remote-jobs`, Himalayas `/jobs/api`, HN "Who is hiring" via hnrss.org, then Working Nomads, Jobicy, Arbeitnow. RemoteOK, Remotive, Himalayas and Jobicy require visible credit and a link back; Remotive allows ~4 calls a day and delays jobs 24h. Stay keyless.
3. **More ATS boards** (S each). `search_boards.py` only does Greenhouse, Ashby and Lever, and reports any HTTP error (even 429) as a dead slug. Add Workable, SmartRecruiters, Recruitee, Workday (POST), Keka, Darwinbox, and separate "dead" from "temporarily failing".
4. **Source health checks** (S-M). Flag boards that return zero jobs or errors. jobhive alone has ~82 dead entries.
5. **Posting legitimacy screen** (S-M). career-ops has 22 signals (fake recruiters, candidate-paid fees, unpaid placement, agency licensing). Most valuable for contract leads.
6. **Liveness check and repost detector** (M). Plain HTTP; today Closed is set by hand. Repost = same company and title on 2+ scan dates within 90 days.
7. **Fit score per ledger row** (S). 0-100 score, a reason, and a "missing or unclear" list; mark provisional for stub postings (JobSync convention).

### Next
8. Status-transition history (append-only log), then funnel timing, follow-up cadence and rejection latency on top (M).
9. Automated truth check on resumes and answers against the profile (M). Enforces non-negotiable 1.
10. Two-pass triage with a compact profile brief, and a deterministic pre-rank so Claude reads only the top matches (S-M). Cuts tokens on big harvests.
11. Email routing with confidence tiers: 95+ auto-update, 50-94 review queue, below ignore (M). Plus applied-duplicate detection (same company and title, 90+ similarity, 30 days).
12. Form-answer improvements from AIHawk/GodsScion: synonym map in `find_answer.py` (visa, sponsorship, work permit), a field-type column in Learned answers, a three-way work-authorization split, missing template rows (drug test, background check, relocation, veteran, disability), pre-upload file check, rehearsal mode that stops at the review page (S each).
13. Deterministic posting screen for clearance, citizenship and staffing-agency wording, with silence on sponsorship not counted as refusal (M).
14. Voice-DNA file (banned words, anti-AI-slop rules) and a cover-letter flow reused as a gig proposal drafter (S).
15. Source analytics: reply rate by source (M).
16. Interview prep, offer/contract reading and negotiation modes from career-ops (S-M; mostly prompt text, mind the attribution).
17. Refresh `docs/CAREER-OPS.md`: it claims reuse of scan, liveness and follow-up that no engine tool actually calls.

### Gigs (new work, no upstream solves it)
- Ledger needs a `kind` column (job or gig) plus rate and duration fields, and a day/hour rate floor derived from the tenant's salary.
- Machine-readable gig sources are few: HN "Who is hiring" filtered on contract/remote, and the Freelancer.com RSS (discovery only; its terms ban auto-bidding). The HN "Freelancer? Seeking freelancer?" thread may have stopped in Oct 2025; verify before building a parser.
- Account-gated and human-run: Upwork, Toptal, Gun.io, Contra, Arc, Lemon.io, Wellfound. The owner signs up once in the BrowserOS neo browser; the engine drafts proposals for approval and never auto-bids.
- YC Work at a Startup is reachable through the Alexandria provider `ycombinator-com`.
- India: use remote feeds with location filters (Himalayas location/timezone restrictions, Remotive required-location). Naukri, Instahyre and Cutshort have no free API.

## Not worth adopting now
career-ops plugin engine, batch runner and token tiers, 19-language modes, 8-CLI support, hired wall, Go TUI; job-ops tracer links, challenge viewer, billing, Docker packaging, visa-sponsor registers (unless a tenant needs sponsorship there).

## Risks to remember
- Terms-of-service risk falls on the user; career-ops forbids LinkedIn workarounds and so do we.
- Unofficial endpoints (Indeed key, Naukri RSA key, Hiring Cafe) can break any week.
- Our Python floor is 3.9; JobSpy and ats-scrapers need 3.10/3.11. If ever adopted: isolated venv, exact hash-pinned versions, subprocess adapter emitting JSONL into the ledger tools.
- Plugin-registry entries in career-ops are third-party repos nobody audited here.
