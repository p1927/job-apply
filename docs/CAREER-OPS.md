# career-ops integration

Engine: `../career-ops` (fork `p1927/career-ops`), installed by the setup skill. Claude maintains it. Each tenant owns all state in its own folder: the ledger, applications, answers, resume and rules. career-ops is optional tooling, run from its own folder with the tenant's data root:

```bash
CAREER_OPS_ROOT="$(python3 tools/tenant.py path)/career-ops" node <script>.mjs
```

so two people never share a cv, profile, tracker or reports.

What we reuse from it:
- Onboarding and intake (`intake.mjs`, `doctor.mjs`, profile templates) when building a new tenant from a CV and LinkedIn export.
- Portal scanning (`scan.mjs`, `portals.yml`) as an extra discovery source; results still go through the ledger.
- Posting checks (`node check-liveness.mjs <url>`), interview prep, follow-up cadence and reply watching.

What we do not use: its `applications.md` tracker. The tenant's ledger and `data/applications.json` are the single source of truth.

`tools/sync_career_ops.sh` rebuilds the tenant's `career-ops/cv.md` from its resume and runs the health check. Never commit `cv.md` into the engine repo. The same rules in the tenant's `REQUIREMENTS.md` apply to anything run through career-ops.
