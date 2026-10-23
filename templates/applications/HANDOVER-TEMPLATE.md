# Handover: job search for {Name} (YYYY-MM-DD)

Copy this file to `applications/HANDOVER-YYYY-MM-DD.md` at session end if work is left half-done. Keep it short and point to data instead of copying it.

## Date
YYYY-MM-DD, written by (agent/session).

## Approval policy
See `REQUIREMENTS.md` (approval policy). Note here only a deviation, such as an application the candidate asked to hold.

## Applied
Source of truth: `data/applications.json` (status Applied and later) and `data/seen-jobs.csv` (status Applied with `app_id`). Do not list them here. Mention only applications submitted this session that are not yet recorded.

## Blocked on a human
From ledger rows with `blocker` set. One line each: APP id or job id | company | blocker (captcha, account, upload, fact, other) | exact question or step | where the form was left.

## Search position
See `data/search-queue.json`. Name the first entry not done and any entry marked rate-limited.

## Open conflicts
Mismatches `tools/check_consistency.py` or you found that are not fixed yet: what, where, what you tried.

## What to do first
1. `python3 tools/tenant.py show` (confirm the right person), `python3 tools/sync.py --pull`, `python3 tools/check_consistency.py`.
2. Ask the blocked items above (one batch).
3. Resume the search at the first open queue entry.
