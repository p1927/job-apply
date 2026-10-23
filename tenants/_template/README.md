# {{NAME}}: job search data

This folder is one person's private job-search workspace. Nothing here is shared with any other person's workspace.

- `tenant.json`: who this is and how the board labels things.
- `REQUIREMENTS.md`: the rules a role must pass, the approval policy and the "Ask the human" table.
- `candidate-profile.md`: the facts and truth rules. Only these facts go in a resume or an answer.
- `applicant-details.md`: personal data, standard answers and learned answers for forms.
- `resume-content.json`, `resume.md`: resume content and the built base resume.
- `data/`: `seen-jobs.csv` (every job seen: status, reason, blocker), `applications.json` (every application), `search-queue.json`, `boards.json`, `vocab.overrides.json`.
- `applications/`: one company file per application, plus the tailored resumes.
- `board/index.html`, `applications-ledger.md`: generated views. Open the board in a browser.
- `career-ops/`: this person's data root for the optional career-ops tools.

Say "find jobs" or "apply" in Claude and the job-search skill does the work.
