# Survey: AIHawk and GodsScion LinkedIn bots, what job-apply can borrow

Read-only. Nothing was run or installed. Engine files untouched.

## Provenance (read this first)
- The scratchpad clone `up/Auto_Jobs_Applier_AIHawk` (HEAD ef69f5e, 2026-10-14) is NO LONGER a job bot. The upstream repo was
  repurposed into "invisible_dots" (self-hosted agent VMs with an anti-bot-detection Firefox, TypeScript/Python, 418 commits since
  2026-09-30, no job code in any branch or tag). Its README says "Built to be undetectable by anti-bot systems", i.e. the project
  now sells detection evasion. There is nothing to borrow from it for forms or prompts.
- The real AIHawk code was read from the fork snapshot `11844/Auto_Jobs_Applier_AIHawk` @ 1cecff3 (2024-10-29), cloned to
  `up/old-aihawk` (read only). Files: `src/aihawk_easy_applier.py` (869 lines), `src/aihawk_job_manager.py`, `src/llm/llm_manager.py`,
  `src/strings.py` (prompts), `src/job_application_profile.py`, `main.py`, `data_folder_example/*.yaml`. The resume/cover PDF builder
  was an external lib (`resume_generator_manager`), not in this snapshot, so resume rendering is not assessed.
- GodsScion/Auto_job_applier_linkedIn: README plus `docs/config-{settings,questions,search,secrets}.md` and `docs/legal.md` read via
  raw GitHub. No source code read. MIT since Aug 2026 (earlier AGPL).

## Ideas table

| idea | file | how it works | do we have it? | effort | worth it? |
| --- | --- | --- | --- | --- | --- |
| Dry run: fill everything, stop at Review, discard, count as skip not failure | GodsScion `stop_before_submit` (docs/config-settings.md) | Flag fills the whole form, halts at the review step, discards. Overrides the pause-before-submit dialog | Partly. Approval mode `each` asks before submit, and we read every field back. No explicit "rehearsal" mode that logs would-be answers per ATS without a ledger row | S | Yes. Add a "rehearse" mode to the skill: fill, read back, write answers to the company file as `draft`, do not submit. Good for new ATS types and new tenants |
| Pause on a failed/unanswerable question, with the exact question shown | GodsScion `pause_at_failed_question`, `pause_before_submit`; forced off when headless "since the safety pauses cannot work with no window" | Dialog box blocks the run until the human answers | Yes, stronger: "Ask the human" table, blockers `fact/other`, find_answer first, batched asks | none | No. Keep ours. Borrow only the design point: pauses must never be silently disabled in unattended mode (we fail to a blocker instead) |
| Question-type router: LLM picks which resume section answers the question (13 sections) then answers from only that section | AIHawk `llm_manager.answer_question_textual_wide_range` + `strings.py` section templates | Step 1 classify question into Personal / Self-ID / Legal / Work prefs / Education / Experience / Projects / Availability / Salary / Certs / Languages / Interests / Cover letter; step 2 answer with only that section as context | Equivalent by hand: `find_answer.py` greps profile, details, requirements, earlier answers | M | Maybe. Useful idea is "answer from ONE section, give the model nothing else", which limits invention. Could add section tags to `applicant-details.md` and have `find_answer.py` print the section heading with each hit. Do not copy the prompts (see NOT copy) |
| Field-type dispatcher: file / radio / text / numeric / date / dropdown / checkbox-terms, each with its own handler and its own answer-cache key `(type, normalised question)` | `aihawk_easy_applier._process_form_section`, `_is_numeric_field`, `_find_and_handle_*` | Detects control type from DOM, normalises label text (lowercase, strip quotes/control chars), looks up `answers.json` by type + question, else asks the LLM, then saves | Learned answers table keyed by question pattern only, no field type; ATS playbook covers per-system widget quirks | S | Yes, small: add a `type` column (text, number, radio, select, date, checkbox) to the Learned answers table in `learn_answer.py` and `find_answer.py`. A "5" for a number box and "5-7 years" for a select are different answers to the same question |
| Option snapping: answer must be one of the options; reject placeholders ("Select an option"); map to nearest option by Levenshtein | `options_template` + `GPTAnswerer.find_best_match` | Prompt forbids choosing placeholder; then nearest-edit-distance option is chosen | Playbook says click the exact option and read back; known bad matches (Man/Woman, India/British Indian Ocean Territory) | S | Partly. The placeholder blacklist is worth copying as a checklist item. Nearest-edit-distance auto-snap is NOT (it silently picks wrong options). If a helper is built, it must return "no confident match" and fall back to a human ask |
| Form error retry with a "fix the input" prompt (shorten text, give a whole number) | `strings.try_to_fix_template` (defined but never called in this snapshot), `_check_for_errors` | Reads `artdeco-inline-feedback--error`, raises; template intended to rewrite the answer from the error text | Playbook has per-ATS notes; we re-read after submit | S | Idea only: playbook rule "on a field error, quote the error text in the company file and reshape the stored answer (length/number) rather than re-asking". Add as playbook row |
| Rate-limit handling: honour `retry-after` / `retry-after-ms`, default 20-30 s, for LLM and HTTP 429 | `LoggerChatModel.__call__`, easy applier resume loop | Sleep by header then retry forever | We stop at the first 429 and mark the queue entry `rate-limited` (SKILL.md section 2), which is safer | none | No. Ours is better. Note their loop is unbounded (see GAP) |
| Work-preferences/EEO/legal schema in one YAML: self_identification, legal_authorization per region (EU/US/CA/UK: work authorization, requires visa, requires sponsorship, legally allowed), work_preferences (remote, in-person, relocation, assessments, drug tests, background checks), availability.notice_period, salary_expectations.salary_range_usd | `job_application_profile.py`, `data_folder_example/plain_text_resume.yaml` | Dataclasses, every key required | Free-form tables in `applicant-details.md`. Check the template has the per-region "requires sponsorship vs legally authorized" split and assessments / drug test / background check lines | S | Yes as a checklist. Compare `tenants/_template/applicant-details.md` against this key list and add missing rows (drug test, background check, assessments, relocation, veteran, disability, pronouns). Keep prose tables, not a rigid schema |
| Three distinct authorization questions: sponsorship, already-authorized, citizenship status; matched in that order | GodsScion docs/config-questions.md (`require_visa`, `legally_authorized`, `us_citizenship`) | Explicit warning that "legally authorized" is not the inverse of "requires visa"; a visa holder answers Yes to both | Settled-answers table in applicant-details exists (e.g. "permanent resident of Sweden" settles right-to-work) | S | Yes: add one line to the template telling the filler to classify sponsorship / authorized-now / citizenship separately before answering. Cheap, prevents a real wrong-answer class |
| Deterministic posting screen: bad_words, security clearance, sponsorship offered/unavailable phrase lists (offer wins; whole-phrase match, not substring), `current_experience` cap with Master's allowance, about-company bad/good words for staffing agencies | GodsScion docs/config-search.md; AIHawk `title_blacklist`, `company_blacklist`, `location_blacklist` | Regex/phrase lists applied to description and company About text before applying | Our screening is LLM judgment per SKILL.md section 3 plus reason codes `staffing`, `consultancy`, `clearance`, `language`; no code | M | Yes. A `tools/screen_posting.py` (reads posting text, tenant-owned phrase lists in `REQUIREMENTS.md` or `data/screen.json`) that prints candidate reason codes as a first pass; the agent still decides. Two lessons from their docs: whole-phrase matching and "silence is not a refusal" (do not auto-drop postings that say nothing about sponsorship). Also matches our ambiguity rule |
| Company blacklist and "apply once per company" | AIHawk `company_blacklist`, `apply_once_at_company`, `is_already_applied_to_company` | Reads success.json, exact lowercase company match | Ledger plus reason codes `duplicate`, `already-applied`; `coverage.py` matches on company and title | none | No, already covered. Optional: make company dedupe also catch aliases (Inc, AB, Ltd) |
| Shuffle search order, randomised dwell, minimum 5-minute wait per page, longer break every 5th page | `start_applying`, `start_collecting_data` | `random.shuffle(searches)`, `random.uniform(1.5,3.5)` sleeps, `MINIMUM_WAIT_TIME`, inputimeout prompt to skip waits | We pace 2-3 s between requests and stop on first 429 | n/a | No (this is ban-avoidance for a bot; see NOT copy). Our model is: low volume, human-supervised, read-only harvest |
| Daily cap awareness: "LinkedIn caps Easy Apply at about 25/day, so applications are a rationed resource, prioritise" | GodsScion docs/config-search.md (strict sponsorship mode rationale) | Filters spend the daily quota on the best postings | Our rule is apply on company site, not Easy Apply, so no LinkedIn cap | none | Only the principle: rank before apply when any channel is capped |
| Collect-only mode: scrape job data to JSON without applying | AIHawk `--collect` | Writes `data.json` | Ledger harvest via `tools/linkedin_harvest.js` + `coverage.py` | none | No |
| Per-application artifacts (generated resume PDF and cover-letter PDF saved per job, path logged with the job) | `_create_and_upload_resume`, `_create_and_upload_cover_letter`, `write_to_file` | Timestamped PDFs in `generated_cv/`, 2 MB and extension check before upload | Company file records resume used; `make_resumes.py` | S | Small borrow: pre-upload check of size (<2 MB), extension (pdf/doc/docx) and filename in `record_application.py` or the playbook. Many ATS reject silently over 2-5 MB |
| JSON ledgers split by outcome (data / skipped / failed / success) and "never retry a previously failed link" | `write_to_file`, `is_previously_failed_to_apply` | One JSON per outcome | One ledger with status/reason/blocker | none | No (ours is better). Keep the "do not retry a failed posting without a new reason" idea; check ledger `blocker`/`note` already prevents reloops |
| LLM call log with token counts and cost per prompt | `LLMLogger.log_request` -> `open_ai_calls.json` | Appends prompt, reply, tokens, cost (hard-coded gpt-4o-mini prices) | Not needed: Claude is the agent, no per-field API calls | none | No |
| Config validator with clear errors for missing/invalid keys | `main.py ConfigValidator` | Type checks on config.yaml, secrets, folder layout | `tools/verify_tenant.py`, `check_consistency.py` | none | No |
| Control-panel UI for non-technical users | GodsScion `start.command` + local panel on 127.0.0.1 | Tabs: Account, Profile, Search, Filters, Run settings | `tools/dashboard.py` is read-only; setup skill interviews the person | n/a | No. Our design (Claude owns the system) already avoids this |
| Structured logging with rotation, levels, no blocking modal on log failure | GodsScion commit "replace hand-rolled print_lg with stdlib logging" (5 MB x 3) | RotatingFileHandler; locked log file degrades to stderr | Our tools print, git is the log | none | No |

## What to explicitly NOT copy

1. LinkedIn automation of any kind (login, Selenium/Chrome profile reuse, Easy Apply clicking, scroll/click pacing). ToS violation,
   account-ban risk; both READMEs push the risk onto the user. AIHawk uses a persistent Chrome profile with `enable-automation`
   switch hidden (`excludeSwitches`), i.e. evasion; GodsScion's `safe_mode` launches guest profiles. Our rule: no LinkedIn Easy Apply,
   apply on company site, harvest read-only, human-paced.
2. Anything that evades bot detection (hidden automation flags, randomised "human" delays, now the whole invisible_dots project).
   Our non-negotiable 2 (no CAPTCHAs, no accounts) is incompatible with building in evasion.
3. Inventing experience. AIHawk prompts directly instruct the model to fabricate:
   - `numeric_question_template`: "A response of 0 is absolutely forbidden ... provide a minimum of 2 years ... plausible number ...
     infer from university, grades, thesis"; on parse failure it defaults to 3 years (`default_experience=3`).
   - `experience_details_template`: "If it seems likely that you have the experience, even if not explicitly defined, answer as if you
     have the experience."
   - `answer_question_textual_wide_range` for cover letters passes the full resume and asks for "specific examples" with no check
     against a whitelist.
   This is the opposite of our rule 1 (answers only from `candidate-profile.md`). Do not port any of these prompts.
4. LLM answering of self-ID, legal and salary fields. EEO, work authorization and salary are facts only the person knows; AIHawk lets
   the LLM paraphrase them, and its salary example reduces them to "55000." Ours stay stored facts or a human ask.
5. Auto-saving unreviewed LLM guesses into the reusable answer cache (`_save_questions_to_json` writes every LLM answer to
   `answers.json` and later reuses it). A wrong guess becomes a permanent "known answer". Our `learn_answer.py` only saves what the
   human gave or approved.
6. Substring cache matching (`sanitize(question) in item['question']`): short or generic questions match unrelated saved questions
   and return the wrong answer.
7. Nearest-edit-distance option snapping with no confidence floor (`find_best_match`), and ticking the first autocomplete suggestion
   (`ARROW_DOWN`, `ENTER` after every text field). Exactly the failure class our playbook already documents (Oracle country, Man/Woman).
8. Unbounded `while True` retry loops that sleep and retry on any exception (`LoggerChatModel`, resume generation). No human
   escalation, burns quota, can hang a run. Our design: stop, set a blocker, tell the person once.
9. Auto-ticking terms/privacy checkboxes and clicking the last radio as the fallback (`_select_radio` clicks `radios[-1]` when no
   match). Our rule: required consents logged, optional ones unticked, no guessed radios.
10. Autonomous submit at volume ("100+ applications in under an hour", "1000 positions overnight"). Conflicts with our approval modes
    and with employers' tolerance; quality and truthfulness over count.
11. Disabling model safety filters (Gemini `BLOCK_NONE` for all categories) and storing the user's password in `secrets.py`
    (GodsScion optional `username/password`). We never handle passwords.
12. Code licence: the AIHawk fork snapshot is AGPL-3.0 and GodsScion pre-Aug-2026 releases are AGPL; copying prompt text or code into
    the engine would pull in that obligation. Ideas only, rewrite from scratch (GodsScion current MIT is safe to read, still no need to copy).

## GAP lines (bugs/risks found)

- GAP: AIHawk dedupe is dead code. `AIHawkJobManager.seen_jobs = []` is set once and never appended to
  (`src/aihawk_job_manager.py` lines 57, 480, 487), so `is_already_applied_to_job` always returns False and `is_blacklisted`'s
  `link_seen` check never fires. Only the failed.json and success.json (company) checks work. Not our code; recorded as the
  failure mode our ledger-first rule avoids.
- GAP: `strings.try_to_fix_template` is defined but never referenced anywhere in the AIHawk snapshot: form validation errors just
  raise and abort the application (`_check_for_errors`).
- GAP (ours): `tools/find_answer.py` is a plain keyword grep with no synonym map, no field type, and no section label. Mis-wordings
  ("sponsorship" vs "visa" vs "work permit") rely on the agent supplying several wordings; a small synonym table (visa, sponsorship,
  work permit, right to work, authorized; notice, availability, start date; salary, compensation, CTC, expectations) built into the
  tool would remove a recurring human-ask risk. Candidate backlog item, effort S.
- GAP (ours): Learned answers have no field type or option list (see table), so a learned "5" can be reused for a dropdown whose
  options are ranges. Candidate backlog item, effort S.
- GAP (ours): no deterministic first-pass screen for stated hard fails in posting text (clearance, citizenship required, on-site days,
  language, staffing agency). The skill relies on the agent re-reading each posting; a phrase screen would also give a reproducible
  reason code. Candidate backlog item, effort M.
- GAP (ours): no rehearsal / dry-run mode documented for new ATSs or new tenants (GodsScion's `stop_before_submit` is the model).
  Candidate backlog item, effort S.
- GAP (ours): no pre-upload file check (size < 2 MB, pdf/doc/docx, ASCII filename) before `upload`. Candidate backlog item, effort S.
- GAP (process): I did not file backlog items; the engine has no backlog tool reachable from this read-only survey and the brief
  forbids touching engine files. The five "Candidate backlog item" lines above should be filed by the caller (search first).

## Recommended order if the owner wants to act
1. Learned-answer `type` column plus synonym map in `find_answer.py` (S, both are tool-only, no personal data in the engine).
2. Template checklist: three-way authorization split and missing EEO/work-preference rows (S).
3. Rehearsal mode and pre-upload file check as playbook rules (S).
4. `tools/screen_posting.py` with tenant-owned phrase lists (M), whole-phrase matching, "silence is not a refusal".
Everything else in AIHawk and GodsScion is either already covered by the engine or unsafe to adopt.
