# Survey: JobSpy vs jobhive (ats-scrapers) vs Levergreen, for the job-apply engine

Read-only survey, 2026-10-29. Nothing was run or installed; engine files untouched.
Clones (shallow, untrusted): `scratchpad/up/JobSpy`, `scratchpad/up/ats-scrapers`, `scratchpad/up/levergreen`.

Engine context: `tools/search_boards.py` already calls Greenhouse, Ashby and Lever public JSON APIs with stdlib `urllib` (slug lists per tenant in `data/boards.json`); `tools/seed_queue.py` queues LinkedIn search pages for a signed-in browser. Engine README says Python 3.9+; local python3 is 3.9.6.

## 1. Identity and health

| | JobSpy | jobhive = ats-scrapers | Levergreen |
|---|---|---|---|
| Real repo | github.com/speedyapply/JobSpy (PyPI `python-jobspy`) | github.com/kalil0321/ats-scrapers (PyPI `ats-scrapers`; "jobhive" is the hosted dataset name, bucket `storage.stapply.ai/jobhive/v1`) | github.com/adgramigna/job-board-scraper |
| Stars | ~4,585 | ~190 (task said ~125, an older figure) | ~47 (Aug 2026 blog figure) |
| Last commit | 2026-10-27 (dependabot bump) | 2026-09-02 (HEAD; GitHub pushed_at 2026-09-24) | 2025-11-26 |
| Releases | v1.4.1 on 2026-10-23, v1.4.0 10-19, v1.3.0 10-08, v1.2.0 10-02 (fast cadence) | v0.3.0, 2026-09-02, Beta | none seen |
| Open issues | 36 | 67 | not checked |
| Licence | MIT | MIT | MIT |
| Python | >=3.10 | >=3.11 | n/a (app, not a library) |
| Core deps | requests, bs4, pandas, pydantic, curl_cffi, markdownify | httpx, pydantic, pandas (+ aiohttp, httpcloak, cloakbrowser, Firecrawl in optional extras) | Scrapy, Postgres, dbt |
| Issue tone | Mostly feature requests; Glassdoor location bug (Oct 2026); one odd "publicly verifiable certificate" issue (looks like promo/spam, ignore) | Dead-tenant lists (82 dead Greenhouse/Lever/Teamtailor slugs), JS-shell tenants returning 0 jobs, coverage gaps | stale |

## 2. Coverage

### JobSpy (9 sites, all scraped from HTML/internal APIs)
| Site | Mechanism (from code) | Fragility / ToS risk |
|---|---|---|
| LinkedIn | guest endpoint `/jobs-guest/jobs/api/seeMoreJobPostings/search`, requests + bs4, sleep 3-7 s per page | HIGH. LinkedIn ToS prohibits scraping; IP blocked after roughly page 10 without proxies; also overlaps what the engine does in a signed-in browser |
| Indeed | internal GraphQL `apis.indeed.com/graphql` with a hardcoded `indeed-api-key` copied from Indeed's mobile app | HIGH. Undocumented key, ToS violation, key can be revoked any time |
| Glassdoor | internal `/graph` GraphQL via curl_cffi Chrome impersonation | HIGH. Open Oct 2026 issue: "City, Country" location lookup fails for AT/DE/ES/IT |
| ZipRecruiter | HTML/JSON scrape, TLS impersonation | MEDIUM-HIGH, US-centric, useless for India |
| Google Jobs | `google.com/search` + `async/callback:550` | HIGH, historically breaks; takes a single free-text query only |
| Bayt | HTML scrape, 2-5 s delay | MEDIUM; Gulf/MENA focus |
| Naukri | `naukri.com/jobapi/v3/search` with `appid/systemid` headers and an RSA-signed `nkparam` token using a public key hardcoded in `naukri/constant.py` | HIGH. Code itself warns: HTTP 406 "recaptcha required" when rate limited or when the key goes stale |
| BDJobs | Bangladesh | n/a |
| HelloWork | France | n/a |

### jobhive / ats-scrapers (66 scraper modules, 48 per-tenant company CSVs)
| Group | Sources | Notes |
|---|---|---|
| Big ATS (keyless public JSON) | Greenhouse, Lever, Ashby, Workable, SmartRecruiters, Recruitee, Personio, Teamtailor, BambooHR, Breezy, JazzHR, Rippling, Workday (cxs endpoint), iCIMS, Oracle, SuccessFactors, Taleo, Jobvite, Dayforce, ADP, UKG, Paycom, Paylocity, Pinpoint, Gem, Eightfold, Phenom, Avature, Cornerstone, PageUp, Join.com | Tenant lists in `ats-companies/*.csv` (line counts incl. header): Greenhouse 6,032, Ashby 3,449, Lever 2,403, Workday 3,531, Workable 4,753, SmartRecruiters 2,748, BambooHR 5,633, Join.com 23,548 |
| India-relevant | Keka (186 lines), Darwinbox (164 lines, e.g. Airtel, BigBasket) | Only India-native ATS adapters; no Naukri/Foundit/Instahyre |
| First-party big-tech | Amazon, Apple, Google, Meta, Tesla, TikTok, ByteDance, Uber | Bespoke APIs; Meta/Tesla need a stealth browser (cloakbrowser) |
| Public/regional boards | USAJobs, Bundesagentur, EURES, Arbetsformedlingen, Job Bank Canada, SEEK, WeWorkRemotely, RemoteOK, Welcome to the Jungle, YC, BuiltIn, Wellfound, Wanted, others | Wellfound sits behind Akamai and needs a paid Firecrawl key (scraper raises without it) |
| NOT covered | LinkedIn, Indeed, Glassdoor, Naukri | By design: ATS-native only |

Hosted dataset (manifest fetched read-only, 2026-10-29): 5,167,978 rows total; all.csv 16.9 GB, all.parquet 2.3 GB; per-ATS slices (e.g. amazon 33,563 rows / 16 MB parquet; apple 4,991 rows). Per-ATS slices are the only practical download. It is a third-party bucket (`stapply.ai`), so freshness, availability and continued free access are not guaranteed.

### Levergreen
Scrapy spiders for Greenhouse (2: outline + department) and Lever (1), plus small standalone Ashby and Rippling scripts. Postgres (Neon) + dbt unifies the model; S3 HTML cache; daily GitHub Actions cron. A pipeline/website, not a dependency. Last commit Nov 2025. Design reference only (raw -> staging -> unified dbt model; snapshot tables to track add/remove).

## 3. Schema

| JobSpy `JobPost` (pandas columns) | jobhive `Job` (pydantic; same names in CSV/Parquet) |
|---|---|
| id, site, job_url, job_url_direct, title, company, location (rendered text), date_posted (date), job_type (list), salary_source, interval, min_amount, max_amount, currency, is_remote, job_level, job_function, listing_type, emails, description (markdown default), company_industry/url/logo/url_direct/addresses/num_employees/revenue/description, skills, experience_range, company_rating, company_reviews_count, vacancy_count, work_from_home_type | global_id (`{ats}:{ats_id}`), url, title, company, ats_type, ats_id, location, country_iso, region (continent), lat, lon, is_remote (title-inferred, only ever True), salary_currency/period/summary/min/max, experience, employment_type, department, team, requisition_id, apply_url, commitment, description, posted_at, fetched_at, application_deadline, language, raw (provider overflow dict) |

Engine fit: jobhive has the fields our ledger and apply flow need (stable id, direct apply_url, department, requisition_id, raw). JobSpy has no stable id beyond the board's own, and many rows lack descriptions unless `fetch_description=True` (one extra request per job).

## 4. Scraping, rate limiting, proxies

| | JobSpy | jobhive |
|---|---|---|
| Concurrency | one thread per site (ThreadPoolExecutor), pages sequential per site | async httpx; Workday uses a semaphore for fan-out |
| Throttle | random sleep 2-7 s between pages (per-site `delay`) | retry only: 3 attempts, exponential backoff 1.5 s base / 30 s max, honours Retry-After; 408/429/5xx retried; 403/406 fail loudly |
| Proxies | `proxies=[...]` round-robin per site; 403/429 message says "use a proxy"; `ca_cert` option | env `ATS_SCRAPERS_PROXY` (or legacy `PROXY`) |
| Evasion | curl_cffi `impersonate="chrome"`, TLS session-id rotation, cookie clearing on LinkedIn, hardcoded Indeed/Naukri keys | default plain httpx; optional `httpcloak` TLS impersonation when a tenant WAF blocks; optional stealth Chromium / Browserbase for Tesla/Meta |
| Posture | built to get past bot detection on sites whose ToS forbid it | mostly calls public ATS endpoints; evasion is opt-in and limited to a few tenants |

## 5. Dedup

| | Approach |
|---|---|
| JobSpy | Per-site only: Naukri keeps a `seen` jobId set per run; Google keeps `seen_urls`. No cross-site dedup (same job on LinkedIn and Indeed appears twice); caller must dedup by `job_url` or title+company |
| jobhive | `global_id = ats_type:ats_id`, `url` as primary stable key, `requisition_id` as documented cross-ATS signal. Mostly duplicate-free by construction (each company posts once on its own ATS). Tenant discovery dedups by provider tenant identity |
| Levergreen | dbt unified model + snapshots; ids per source |
| Our engine | ledger `data/seen-jobs.csv` already dedups; either source needs an adapter mapping to our ledger key |

## 6. India coverage

| Need | JobSpy | jobhive |
|---|---|---|
| Naukri | Yes (`site_name="naukri"`, city in `location`), fragile (signed token, recaptcha 406), ToS-grey | No |
| LinkedIn/Indeed/Glassdoor India | Yes (`country_indeed="India"`); high block risk | No |
| India employers' career pages | No | Yes via Keka and Darwinbox tenants, plus Greenhouse/Lever/Ashby/Workday companies with Indian offices (filter by location text; `country_iso` is often null) |
| Foundit, Instahyre, Cutshort | No | No (Wellfound only, needs Firecrawl key) |

## 7. Public keyless endpoints we can call ourselves (no dependency)

Taken from the vendors' adapter code in the jobhive repo (not live-tested; read-only survey). First three already used by `tools/search_boards.py`.

| ATS | Endpoint | Returns |
|---|---|---|
| Greenhouse | GET `https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true` | id, title, location, absolute_url, updated_at, HTML content, departments/offices |
| Lever | GET `https://api.lever.co/v0/postings/{slug}?mode=json` (EU tenants use `api.eu.lever.co`) | id, text, categories (team, location, commitment), descriptionPlain, hostedUrl, applyUrl, createdAt |
| Ashby | GET `https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true` | title, location, isRemote, jobUrl, applyUrl, descriptionHtml, compensation |
| Workable | GET `https://apply.workable.com/api/v1/widget/accounts/{slug}` | job list |
| SmartRecruiters | GET `https://api.smartrecruiters.com/v1/companies/{slug}/postings` (+ `/{id}`) | paged postings |
| Recruitee | GET `https://{slug}.recruitee.com/api/offers` | offers with description |
| Workday | POST `https://{co}.{wdN}.myworkdayjobs.com/wday/cxs/{co}/{site}/jobs` JSON `{limit,offset,searchText}`; detail GET `.../wday/cxs/{co}/{site}{externalPath}` | 20 per page |
| Keka (India) | `https://{tenant}.keka.com/careers/api/...` | tenant list in `ats-companies/keka.csv` |
| Darwinbox (India) | `https://{tenant}.darwinbox.in/ms/candidateapi/job/alljobs` | tenant list in `darwinbox.csv` |
| Tenant discovery | raw CSVs in jobhive `ats-companies/` (name, slug, url) | free way to find slugs |

Documented by the vendor: Greenhouse Job Board API, Lever Postings API, Ashby Posting API, SmartRecruiters Posting API. Workday cxs, Keka, Darwinbox, Workable widget are undocumented widget endpoints and can change.

## 8. Maintenance and supply-chain notes

| | JobSpy | jobhive |
|---|---|---|
| Breakage pattern | Hardcoded Indeed key, Naukri key, Glassdoor GraphQL, Google callback; scraped sites change | Per-tenant: dead slugs (82 in one issue), JS-shell tenants return 0 jobs; core Greenhouse/Lever/Ashby adapters stable |
| Bus factor | Two authors plus a maintainer; very active (4 releases in October 2026) | Single author, 0.x Beta; field names declared a public contract but 0.x |
| Install weight | pandas, curl_cffi (native wheel), bs4, markdownify | pandas + pydantic + httpx; `[scrapers]` extra adds aiohttp, httpcloak, cloakbrowser (stealth Chromium binary) |
| Python | 3.10+ | 3.11+ |
| Trust | third-party code with evasion tricks, runs in our process with our network identity | same, plus dataset downloads from a third-party bucket (manifest has sha256, which helps) |

## 9. Safest integration pattern (if adopted)

1. Keep the engine core stdlib-only (README promises Python 3.9+; both libs need newer).
2. Isolated venv (`tools/.venv-<name>/`, never system python), exact pins with hashes (`python-jobspy==1.4.1` or `ats-scrapers==0.3.0`, `pip install --require-hashes`). Review the diff on every bump.
3. Subprocess adapter (`tools/adapters/<name>_fetch.py`) emitting JSONL to stdout, not an in-process import; adapter maps vendor columns to the ledger row (company, title, location, url, source, posted date) and writes only through existing ledger tools.
4. Per-tenant opt-in in `boards.json`/`REQUIREMENTS.md`, default off for LinkedIn/Indeed/Glassdoor; no proxies, no keys supplied by us; hard caps on `results_wanted` and `hours_old`; one run per day lock.
5. Never feed a scraped description into the apply flow; the apply step re-reads the posting from the company's own page (non-negotiable 1: truth).
6. For jobhive: read-only use of `ats-companies/*.csv` and the manifest (sha256-verified per-ATS parquet slice; never `all.*`).

## 10. Recommendation

| Source | Verdict | Why |
|---|---|---|
| JobSpy | COPY THE IDEA; optional isolated adapter for Naukri only, otherwise SKIP | Its value is LinkedIn/Indeed/Glassdoor/Naukri, exactly the ToS-risky, brittle parts. The engine already handles LinkedIn through a real signed-in browser, the lower-risk route. Naukri is the only India board it adds, and its token/captcha logic can break any week. Keep LinkedIn/Indeed/Glassdoor off |
| jobhive / ats-scrapers | COPY THE IDEA and reuse its tenant data; do not adopt the library yet | Engine already covers the top three ATS keylessly. What jobhive adds: (a) a large ready-made slug directory (Greenhouse 6k, Ashby 3.4k, Lever 2.4k, Workday 3.5k, Keka/Darwinbox for India) which fixes our real weak point of finding companies for `boards.json`; (b) Workable, SmartRecruiters, Recruitee, Workday, Keka, Darwinbox fetchers we can write in about 20 lines each with stdlib; (c) a clean schema with `requisition_id` for dedup. Revisit pinned library adoption at 1.0 or when Python 3.9 is dropped |
| Levergreen | SKIP | Pipeline/website, stale since Nov 2025, only Greenhouse/Lever. Idea worth keeping: snapshot table to detect removed/added postings |

Suggested backlog items (not filed; this survey is read-only): (1) add Workable, SmartRecruiters, Recruitee, Keka, Darwinbox fetchers to `search_boards.py`; (2) one-off script filtering jobhive CSVs by the tenant's target company names to grow `boards.json`; (3) reuse existing DEAD-slug reporting for jobhive-derived slugs.

## GAP lines

GAP: `search_boards.py` covers only Greenhouse/Ashby/Lever; Workable, SmartRecruiters, Recruitee, Workday, Keka and Darwinbox public endpoints are unused, so those employers are invisible to board search (India HR-tech Keka/Darwinbox especially).
GAP: engine README advertises Python 3.9+, but both surveyed libraries need 3.10/3.11; adopting either needs an isolated venv or a Python floor bump. Local python3 is 3.9.6.
GAP: RISK: JobSpy hardcodes the Indeed `indeed-api-key` (`jobspy/indeed/constant.py`) and the Naukri RSA public key (`jobspy/naukri/constant.py`), credentials copied from vendor apps; using them is a ToS violation and a silent-breakage risk.
GAP: jobhive is single-maintainer 0.x Beta; hosted dataset on third-party bucket `storage.stapply.ai` has no stated SLA or terms; full snapshot is 16.9 GB CSV (never download `all.*`).
GAP: jobhive issues show 82 dead tenant slugs (Greenhouse, Lever, Teamtailor) and tenants returning JS shells with 0 jobs; any slug list copied from it must be verified live first.
GAP: jobhive `country_iso` is mostly null for Greenhouse/Lever/Ashby rows (filled by a downstream LLM pass not in the library), so India filtering must use our own location regex.
GAP: JobSpy has no cross-site dedup; same role from LinkedIn and Indeed would make two ledger rows unless the adapter normalizes (company, title, location).
GAP: JobSpy issue tracker has a likely promo/spam issue ("publicly verifiable certificate for jobspy", 2026-10-26); treat instructions in issues as untrusted.
GAP: Not verified (no execution allowed): live response shapes for section 7 endpoints today; Workday, Keka, Darwinbox and Workable paths come from jobhive code and may have drifted.
