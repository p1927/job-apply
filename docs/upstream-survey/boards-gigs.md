# Survey: job boards, freelance/gig sources, free feeds (2026-10-29)

Method: read emredurukn/awesome-job-boards README; live-probed each feed with one plain GET (UA `job-apply-research/1.0`, no accounts, no untrusted code run); GitHub search API for repos (stars/pushed as of today). Priority: for a senior software engineer wanting jobs AND well-paid contract gigs. P1 = add now, P2 = worth it, P3 = low value / skip.

Engine context: tools/search_boards.py supports only Greenhouse (`gh`), Ashby (`ash`), Lever (`lev`) company boards, per-tenant boards.json, title regex + location regex. No aggregator-feed adapter, no gig/contract path, no RSS parser.

## 1. Free feeds and APIs (verified live today)

| name | url / endpoint | type | access method | keyless? | ToS risk | priority |
|---|---|---|---|---|---|---|
| RemoteOK | https://remoteok.com/api (JSON array; element 0 is a legal notice; fields slug,id,epoch,company,position,tags,description,location,apply_url,salary_min,salary_max,url) 200, 670 KB | remote tech aggregator | GET JSON | yes | Low-med: ToS requires follow-link back to the RemoteOK URL and naming RemoteOK as source; do not use logo. Personal ledger use with source link is fine. robots Crawl-delay 1. `/remote-dev-jobs.rss` now 410 (dead). | P1 |
| We Work Remotely | https://weworkremotely.com/remote-jobs.rss (all, 900 KB) ; per category e.g. /categories/remote-programming-jobs.rss (25 items), remote-devops-sysadmin-jobs.rss, remote-back-end-programming-jobs.rss etc. | remote aggregator | RSS 2.0 | yes | Low: public RSS, robots allows. No stated API terms; credit source. | P1 |
| Remotive | https://remotive.com/api/remote-jobs?category=software-dev&search=...&limit=N | remote aggregator | JSON | yes | Medium: legal notice says max ~4 requests/day, jobs delayed 24h, must link back + credit, do NOT re-submit to Jooble/Google Jobs/LinkedIn. Fine for private personal use under the cap. Responses cached (no-store header but CF HIT). | P1 |
| Himalayas | https://himalayas.app/jobs/api?limit=N (cursor: `nextCursor` -> `?cursor=`), /jobs/api/search?q=..., check-open: /jobs/api/companies/:co/jobs/:slug (200 open, 410 closed); RSS/Atom https://himalayas.app/jobs/rss. 129k jobs; has seniority, salary, locationRestrictions, timezoneRestrictions | remote aggregator | JSON / Atom | yes (free key optional: 60 req/min, 10k/day; unkeyed share one public pool) | Medium: docs say apply links MUST use the API `applicationLink`, show visible Himalayas credit, do not pass jobs to other boards. Key needs email signup = account creation, so stay keyless. | P1 (best metadata: seniority + country/timezone restrictions) |
| Arbeitnow | https://www.arbeitnow.com/api/job-board-api (+ `?visa_sponsorship=true`, `remote`); UK twin https://www.arbeitnow.co.uk/api/job-board-api | EU/Germany ATS-sourced | JSON, paged (`links.next`) | yes | Low. Header x-ratelimit-limit: 50 (per window), cache-control max-age 5 days. 2 MB per page, so fetch once/day. | P2 (Europe + visa; weak for India-based remote) |
| Working Nomads | https://www.workingnomads.com/api/exposed_jobs/ (41 items now; fields url,title,description,company_name,category_name,tags,location,pub_date) | remote aggregator | JSON | yes | Low-unknown: endpoint is literally named "exposed"; no terms found on scraping; be polite. | P2 |
| Jobicy | https://jobicy.com/api/v2/remote-jobs?count=50&tag=python&geo=...&industry=dev (cursor paging) | remote aggregator | JSON | yes | Medium: notice requires credit with direct link and application buttons must point to the feed job URL. | P2 |
| Python.org jobs | https://www.python.org/jobs/feed/rss/ | Python roles | RSS | yes | Low | P3 (Python only, small) |
| HN Who is hiring | https://hn.algolia.com/api/v1/search_by_date?tags=story,author_whoishiring (find newest thread id), then https://hacker-news.firebaseio.com/v0/item/<id>.json -> `kids` comments; or https://hnrss.org/whoishiring/jobs?q=senior (RSS/JSON Feed, filters q=, points=) | startup + remote, many senior | JSON / RSS | yes | Low: official public HN Firebase API; hnrss is a third-party service (be gentle). Oct 2026 thread id 49922569. | P1 (high signal, many direct-email applies) |
| HN Freelancer? Seeking freelancer? | same Algolia query, `query=freelancer` | contract gigs | JSON | yes | Low | P2 but see GAP-1 |
| Freelancer.com new projects | https://www.freelancer.com/rss.xml (200; items carry title, description with budget and skill tags, category per skill; `?keyword=python` returned 200 but filtering not verified) | gig/projects | RSS | yes | Medium: public RSS, but bidding requires an account and Freelancer ToS bans auto-bidding. Discovery only. Low pay on average. | P3 |
| Upwork | RSS feeds DISCONTINUED 2024-08-20 (https://support.upwork.com/hc/en-us/articles/52052528243731-RSS-deprecation). /ab/feed/jobs/rss now 403. Official GraphQL API needs approved key + OAuth account. | gig marketplace | none keyless | no | High: ToS forbids scraping/automation; every scraper repo below needs login. | P3 as a source; use only for human-driven browsing + alerts inside the user's own account |
| Reddit r/forhire | https://www.reddit.com/r/forhire.rss (200 Atom). `.json` endpoint returned 403 to a non-browser UA. | gigs (mixed quality, many low-budget) | Atom | yes | Medium: Reddit API terms; RSS ok at low rate. | P3 |
| The Muse | https://www.themuse.com/api/public/jobs?page=1 (500 req/h, header x-ratelimit-limit) | general | JSON | yes | Low | P3 (few eng roles, US-centric) |
| Remote Jobs API (tten.no) | https://remote-jobs-api.tten.no | meta-aggregator of Remotive+RemoteOK+Jobicy+WWR+HN | JSON | yes | Unknown/third party; re-aggregates the others' data, so their credit and no-redistribution clauses still apply. Prefer originals. | P3 |
| Y Combinator Work at a Startup | https://www.workatastartup.com/jobs returns 406 to curl. Account-gated for apply. Alexandria provider `ycombinator-com` capability `companies/job_search` (via firecrawl_scrape alexandria) searches YC jobs sitemap with remote/role/country filters, up to 120 pages/30 s per call. | startup | alexandria or browser | via alexandria yes | Medium: WaaS web is login-gated for apply; the sitemap-based provider is read only. | P1 via alexandria (cost: credits), else browser |
| Wellfound | https://wellfound.com/jobs (200 HTML 250 KB but DataDome-protected; JS app) | startup | browser only | no for apply | High: ToS bars scraping; bot-detection. Never automate; human-in-browser search only. | P2 manual |
| Greenhouse/Lever/Ashby | already supported | company ATS | JSON | yes | Low (public job-board APIs) | already done; widen slug lists (see section 4) |
| Others in ATS family not yet in engine | Workable (`apply.workable.com/api/v1/widget/accounts/<slug>`), SmartRecruiters (`api.smartrecruiters.com/v1/companies/<slug>/postings`), Recruitee (`<slug>.recruitee.com/api/offers/`), Personio XML, Teamtailor, JOIN | company ATS | JSON/XML | yes | Low (public posting endpoints; Alexandria also has providers workable, join-com) | P1 as adapters (GAP-3) |

Other feeds seen but not probed: Jobspresso, Remote.co, NoDesk (no public API found), Jooble API (403 keyless, needs key), Adzuna (needs key; India supported, free tier), Findwork.dev (401, needs key), USAJobs (US-only).

## 2. Boards from awesome-job-boards worth adding

Section names are from the README. Only ones relevant to a senior software engineer; anything that is a resume tool or non-tech niche is ignored. "Feed" column: whether a machine-readable path is documented in the README or known.

### 2a. Remote tech
| name | url | type | access | keyless? | ToS risk | priority |
|---|---|---|---|---|---|---|
| We Work Remotely | weworkremotely.com | remote | RSS (verified) | yes | low | P1 |
| remote OK | remoteok.com | remote | JSON (verified) | yes | low-med | P1 |
| Remotive | remotive.com | remote | JSON (verified) | yes | med | P1 |
| Working Nomads | workingnomads.com/jobs | remote | JSON (verified) | yes | low | P2 |
| Jobicy | jobicy.com/jobs | remote | JSON (verified) | yes | med | P2 |
| Himalayas (not in list but best) | himalayas.app | remote | JSON/Atom | yes | med | P1 |
| Remote.com | remote.com/jobs/all | remote (EOR company) | HTML | n/a | med | P2 manual |
| Real Work From Anywhere | realworkfromanywhere.com | global WFA | HTML | n/a | med | P2 (good for India-based) |
| JustRemote, DailyRemote, Remote Index, Remote100K, RemoteRocketship, NoDesk, Remoters, SkipTheDrive, Jobspresso, remote.co, DynamiteJobs | various | remote | HTML only, no public API known | n/a | med (scraping) | P3 (aggregators of the above; duplicate) |
| Remote Python / Ruby On Remote / Remote JavaScript Jobs | remotepython.com etc | stack-specific remote | HTML | n/a | med | P3 unless tenant stack matches |
| Devremote, Remote Developer Jobs, Remote Hunt, RemoteHunt (scores vs resume), Remote Landers, WeWorkFromHome (rebroadcasts GH/Lever/Ashby) | various | remote | HTML | n/a | med | P3 (WeWorkFromHome and Remote Landers are derived from ATS boards the engine already reads) |
| RemoteYeah, Remote Index, tryremotely | various | remote | HTML | n/a | med | P3 |
| established-remote (GitHub list) | github.com/yanirs/established-remote | curated remote companies | Markdown list | yes | low | P1 for seeding boards.json slugs |
| Present of AI | presentofai.com/jobs | AI roles, 9,600+ | free public API, MCP server, XML feed per README (unverified) | claims yes | unknown | P2 (verify) |
| Headcount Labs | headcountlabs.com | 8.4M postings API + MCP, first 100k records/month free | API key presumably (unverified) | maybe | unknown, key = account | P3 (account) |
| YubHub | yubhub.co | jobs from employer career pages, free API/RSS/JSON/XML | claims yes (unverified) | yes? | unknown | P2 (verify) |

### 2b. Startup
| name | url | type | access | keyless? | ToS risk | priority |
|---|---|---|---|---|---|---|
| YC Work at a Startup | workatastartup.com | YC startups | browser or alexandria provider | via alexandria | med | P1 |
| Wellfound | wellfound.com/jobs | startups | browser (human) | no | high for automation | P2 |
| Startup.jobs | startup.jobs | startups | HTML | n/a | med | P2 |
| Underdog.io | underdog.io | curated high-growth; needs a profile (account) | none | no | n/a | P3 (account) |
| The Hub | thehub.io | Nordic startups | HTML | n/a | med | P3 |
| EU-Startups Job Board | eu-startups.com/startup-jobs | EU startups | HTML | n/a | med | P3 |
| VCBacked Startup Jobs | vcbacked.co/startup-jobs | recently funded | HTML | n/a | med | P2 |
| DMtheFounder | dmthefounder.com | founder-posted eng roles from X/HN | HTML | n/a | low | P2 |
| WorkInStartups, StartUpers, Startups Gallery, Basin.cv, devtooljobs, Hypetrain | various | startups | HTML | n/a | med | P3 |
| Levels.fyi jobs | levels.fyi/jobs | pay-transparent, senior bands | HTML/JS | n/a | med-high | P1 for salary checks (human browsing) |
| easy-application | github.com/j-delaney/easy-application | 400+ SWE companies list | Markdown | yes | low | P1 to seed ATS slugs |

### 2c. Contract / freelance (README "Freelancer" + "Creative & Gig" + AI contractor)
| name | url | type | access | keyless? | ToS risk | priority |
|---|---|---|---|---|---|---|
| Toptal | toptal.com | vetted marketplace, high pay, screening process | apply via account | no | n/a | P1 as a human-action step (one-off vetting application); not scrapeable |
| Gun.io | gun.io | vetted US-oriented dev contracts | account application | no | n/a | P2 |
| YunoJuno | yunojuno.com | UK vetted freelance | account | no | n/a | P3 (UK work-eligibility) |
| Upwork | upwork.com | marketplace | login | no | high for automation | P2 manual only (see section 1) |
| Freelancer.com | freelancer.com | marketplace | RSS discovery | yes (RSS) | med | P3 |
| Guru, PeoplePerHour, Fiverr, Hubstaff Talent, Outsource, Techamana, GigGrabbers | various | marketplaces | login | no | med-high | P3 (race to bottom pay) |
| Gridnaut Recruiting | gridnaut.site/jobs | AI-training contractor roles, hourly $23-180, Mercor referrals | HTML | n/a | low | P2 (expert hourly contracts; check pay vs rule) |
| Specialist AI Work | specialistaiwork.com | AI eval/expert-review contracts with pay and eligibility | HTML | n/a | low | P2 |
| SideQuest Board | sidequestboard.app | gigs aggregated from public communities | HTML | n/a | low | P2 |
| Only Hiring | onlyhiring.hassandev.me | r/forhire etc with scam score | HTML | n/a | low | P2 |
| Human Pages | humanpages.ai | directory for agents hiring humans | n/a | n/a | n/a | P3 |
Not in the README but relevant: Contra (commission-free independent pro network, profile = account), Arc.dev, Turing, Lemon.io (appears as an advertiser in feeds above), Braintrust, Wellfound contract roles, Codementor, Crossover. All need accounts; only discoverable manually.

### 2d. India-friendly
README India section is thin (PrepNPlaced apprenticeships, InternDoor: interns only; skip). Useful:
| name | url | type | access | keyless? | ToS risk | priority |
|---|---|---|---|---|---|---|
| India Tech Jobs | github.com/landedjobs/india-tech-jobs | software/AI roles in India and India-eligible remote, "refreshed" by repo | Git repo data files (likely JSON/MD; not inspected) | yes | low | P1 (read, then consider a parser) |
| AbroadStack | abroadstack.com/jobs | remote, visa-friendly overseas | HTML | n/a | med | P2 |
| Real Work From Anywhere | realworkfromanywhere.com | WFA global | HTML | n/a | med | P2 |
| Himalayas locationRestrictions/timezoneRestrictions fields | (feed above) | lets the engine drop US-only roles | JSON | yes | med | P1 |
| Remotive `candidate_required_location` ("Worldwide", etc.) | (feed above) | filter | JSON | yes | med | P1 |
| DoableFromHome, Remotejobify, Covesight, RoleSense, Remote Jobs hire-country checkers | various | country eligibility checked | HTML | n/a | med | P3 (use as manual cross-check) |
| Jaabz | jaabz.com | visa sponsorship/relocation tech | HTML | n/a | med | P3 |
Not in README but India-specific: Naukri, Instahyre, Cutshort, Hirist, Foundit, Wellfound India, LinkedIn India. None have free official APIs; Instahyre/Cutshort need accounts. Adzuna API (needs key) covers India.

### 2e. AI / senior engineering niche boards (README AI, DevOps, Programming)
| name | url | access | priority |
|---|---|---|---|
| AI Dev Jobs | aidevboard.com ("REST API for agents", unverified, 5000+ roles w/ salary) | API claimed | P1 verify |
| Agentic Engineering Jobs | agentic-engineering-jobs.com | HTML | P2 |
| Jobs in AI, AI Jobs (moaijobs), ExploreJobs.ai | various | HTML | P3 |
| Next Level Jobs EU (EUR 100k+), Euro Top Tech Jobs, Jobs Brief (EU senior cloud/DevOps remote), Remote1st Jobs | various | HTML | P2 for senior filter |
| Golang/Python/Rust/TS stack boards (golang.cafe returned 429 to curl, python.org/jobs ok) | various | HTML/RSS | P3 unless stack matches |
| NoFluffJobs (Poland, salary-transparent; https://nofluffjobs.com/api/posting returns 115 MB JSON, do NOT fetch full) | api | keyless | P3 |

## 3. Open-source repos: freelance / gig discovery and proposals
Stars and last push from GitHub API today (2026-10-29). None were executed or cloned. Verdict column = reuse value for this engine.

| repo | stars | last push | what it does | verdict |
|---|---|---|---|---|
| github.com/roperi/UpworkScraper | 68 | 2026-10-21 | scrapes best-match Upwork postings (logged-in), MIT | idea only; needs Upwork login/ToS risk |
| github.com/DykstraBruno/workaholic | 62 | 2026-06-14 | aggregates and filters freelance listings from Upwork, Workana, 99Freelas, LinkedIn, Indeed, Gupy by keywords | architecture reference; Brazil focus; no licence file (do not copy code) |
| github.com/richardadonnell/Upwork-Job-Scraper | 47 | 2026-05-23 | "No Upwork RSS? No problem": browser-extension style scraper+tracker | idea only |
| github.com/asaniczka/Upwork-Job-Scraper | 33 | 2026-04-11 | archives all Upwork jobs for analysis | ToS-risky; analytics only |
| github.com/hashiromer/Upwork-Jobs-scraper- | 33 | 2025-06-27 | Go fetcher of new Upwork jobs | stale-ish |
| github.com/sudhamjayanthi/upwork-job-scraper | 38 | 2021-10-11 | terminal browsing | dead |
| github.com/orgupdate/Apify-Upwork-Jobs-Scraper | 23 | 2026-10-05 | Apify actor (paid platform) | skip |
| github.com/oldravian/upwork-job-alerts | 6 | 2024-07-23 | PHP: poll Upwork RSS, email new jobs | dead (RSS gone Aug 2024) |
| github.com/akashrchandran/upwork-notifier-bot | n/a (search hit, not queried) | n/a | RSS to Telegram | dead for same reason |
| github.com/ArthurPatriot/upwork-rss-informer | 4 | 2020 | RSS to Telegram | dead |
| github.com/leulabay1/upwork-notifier | 2 | 2026-09-01 | Chrome extension polling the user's own "Most Recent" feed every 5-10 min | works inside user's logged-in browser; closest to ToS-tolerable alert |
| github.com/talhapythoneer/upwork-scraper-jobalerts | low | 2026-10-04 | Selenium Upwork alerts | ToS-risky |
| github.com/yuvraj-xyz/upwork-proposal-bot | 1 | 2026-05-17 | Upwork monitor + Claude Haiku/Sonnet proposal generator + Telegram | pattern reference for proposal drafting |
| github.com/nusRying/Elite-Upwork-Proposal-Generator | 11 | 2026-03-14 | TypeScript proposal generator | pattern only |
| github.com/an0moly/ai-upwork-proposal-generator | 2 | 2024-01-11 | fine-tunes GPT-3 on own past proposals | outdated |
| github.com/ElenkaSan/n8n-proposal_generator | 2 | 2025-06-02 | n8n workflow: pull posts, draft proposals | pattern |
| github.com/thesarinjaizz09/freelancer-autobidder | 1 | 2025-10-23 | Selenium auto-bidder on Freelancer.com (logs in) | do not use: login + auto-bid violate this repo's non-negotiables |
| github.com/painbot-coin/freelancer_telegram_bid_bot | 0 | 2026-09-18 | Freelancer.com search + auto bids to Telegram | same |
| github.com/sonu831/job-auto-apply-bot, MSarfarazMeyo/upwork-auto-apply-bot | 0 | 2026 / 2023 | auto-apply bots | do not use |
| github.com/naeemsabir1/DevHunt | 4 | 2026-04-18 | AI-scored aggregator of 13 platforms (MIT) | architecture reference |
| github.com/rkaran112/gig-scanner | 0 | 2026-07-23 | FastAPI GUI over a Reddit gig-post scanner (r/forhire, r/slavelabour) | pattern |
| github.com/MaxwellVolz/hn_whos_hiring | 11 | 2026-10-02 | ranks every HN "Who is hiring" post against your resume, drafts emails, prefills applications locally | closest match to this engine's need; read for design, then reimplement |
| github.com/jordinl/hnhiring | 18 | 2026-04-29 | Ruby index of HN Who is hiring | data model reference |
| github.com/gabfl/hn-whoishiring | 10 | 2024-10-09 | FastAPI app to manage WIH postings | reference |
| github.com/dheerajck/hnwhoishiring | 15 | 2026-09-05 | JS viewer | reference |
| github.com/gaganpreet/hn-hiring-mapped | 37 | 2018 | map view | dead |
| github.com/lukasz-madon/awesome-remote-job | 50,068 | 2026-09-21 | curated remote jobs and resources | read for company lists |
| github.com/alros/awesome-remote-jobs | 8 | 2026-10-28 | SWE-focused remote board list (Shell) | check for lists |
| github.com/wickfeed/ats-job-aggregator | 0 | 2026-07-16 | monitor for Greenhouse, Lever, Ashby, Workable, Recruitee via official JSON | shows the ATS endpoints to add (GAP-3) |
| github.com/ququyixiaozei/aijobs | 2 | 2026-10-28 | daily scraper for GPU/ML-systems jobs at AI labs | niche |
| github.com/mergisi/awesome-openclaw-agents (upwork-proposal SOUL.md) | n/a | n/a | prompt text for a proposal-writing agent (200-word proposals, open with the client's problem, one specific question) | prompt ideas only |
Hosted tools seen (not repos, all paid/accounts): Upwex, UpHunt, GigRadar, Vibeworker, GigUp, OutBid, Apify actors. They exist because RSS died; they require Upwork login or scrape.
HN Algolia search for a "Freelancer? Seeking freelancer?" parser found no dedicated repo. The `hnrss.org/whoishiring/jobs` feed and the HN Firebase API cover it.

## 4. Suggested additions to the engine (not done; engine files untouched)
1. New `tools/search_feeds.py` (or a `feed` provider in search_boards.py) reading: RemoteOK JSON, WWR RSS (programming, devops, back-end, full-stack categories), Remotive (`category=software-dev`, max 4 calls/day), Himalayas JSON (filter `seniority`, `locationRestrictions` incl. empty or India/Worldwide, `timezoneRestrictions` including UTC+5:30 band), Working Nomads JSON, Jobicy JSON, Arbeitnow (remote + visa).
2. Source and credit field in the ledger row (source name + canonical URL), because RemoteOK, Remotive, Himalayas and Jobicy require attribution; apply via Himalayas `applicationLink`, and drop closed jobs through the Himalayas 410 check.
3. New "contract" track: HN Who is hiring (`hnrss.org/whoishiring/jobs?q=contract` or Firebase + regex for REMOTE/CONTRACT/INTERN), HN Freelancer thread, Freelancer.com RSS (discovery only), Gridnaut/Specialist AI Work (manual), plus human-run steps for Toptal/Gun.io/Contra vetting applications.
4. Add ATS adapters: Workable, SmartRecruiters, Recruitee, Personio, Teamtailor/JOIN (all public posting endpoints).
5. Seed boards.json slugs from easy-application, established-remote, awesome-remote-job.

## GAPs
- GAP-1: HN "Freelancer? Seeking freelancer?" threads: Algolia shows the newest at Oct 2025 while "Who is hiring" continues to Oct 2026 (id 49922569). The freelancer thread may have stopped or moved; verify before building a parser.
- GAP-2: Upwork has no keyless, ToS-safe discovery path since 2024-08-20. Any Upwork integration must run in the user's own signed-in browser with human approval; the engine's no-accounts rule means only the user can log in. Do not adopt any scraper/auto-bidder repo listed above.
- GAP-3: search_boards.py supports only gh/ash/lev; Workable, SmartRecruiters, Recruitee, Personio, Teamtailor, JOIN and all aggregator feeds are unreachable. It also uses `urllib` with `User-Agent: Mozilla/5.0` and silently treats any failure as "DEAD" (no HTTP status, no rate-limit handling), so a 429 looks identical to a wrong slug.
- GAP-4: attribution/redistribution terms (RemoteOK, Remotive, Himalayas, Jobicy) are not represented anywhere in the engine; Remotive's 4-calls/day cap and 24h delay and Himalayas's "use applicationLink" rule would be violated by a naive hourly poller.
- GAP-5: Remotive says do not submit its jobs to LinkedIn/Jooble/Google Jobs; the tenant board/dashboard is private, so fine, but never forward feed jobs into any public output.
- GAP-6: unverified claims in the README (YubHub, Present of AI, AI Dev Jobs, Headcount Labs free APIs; India Tech Jobs repo format) were not probed; verify before relying on them.
- GAP-7: nofluffjobs `/api/posting` is 115 MB per call and Arbeitnow pages ~2 MB; unbounded fetches would hang the 20 s timeout.
- GAP-8: GitHub unauthenticated search hit its rate limit (60/h) during this survey, so some repo queries (reddit forhire bots, remote job API scrapers) returned nothing; star counts above are from the calls that succeeded.
- GAP-9: Several README boards (golang.cafe 429, Wellfound 200 behind bot protection, workatastartup 406) reject plain HTTP clients; they need the browser path and per-site pacing.
