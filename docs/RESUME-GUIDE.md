# Resume Guide

How the resumes in this repo are built, and why. Built by `tools/make_resumes.py` (one base resume plus tailored variants).

## What the research said (searched 2026-10-21)
Sources: JobWizard, Roleframe, AIApply, RecruitBPM and ATS Verification on formatting; Enhancv and FreeCV on how recruiters spot AI-written resumes; LevStack, Careery and a Medium post by Fahim ul Haq on AI engineer resumes.

ATS formatting
- One column, top to bottom. No tables, text boxes, icons, photos or graphics.
- Plain fonts (Arial, Calibri, Helvetica, Georgia), body 10 to 12 pt, name up to 18 pt.
- Standard headings: Professional Summary, Professional Experience, Technical Skills, Projects, Education.
- Contact details in the body, not in a header or footer. Full month and year on every date.
- Text-based PDF exported from a real document, not a design tool. Test: select a sentence, or copy and paste into a plain text editor and check the order.
- Clear file name: `<Full_Name>_<Company>_Resume.pdf`.

Sounding human
- The usual tells are the em dash, filler words (leverage, utilize, spearhead, results-driven, passionate, robust, seamless), bullets that all have the same shape, and a summary that could belong to anyone.
- Specific beats polished: name the system, the tool and the constraint. Vary bullet length. Use plain verbs (built, set up, wrote, moved).
- Do not keyword-stuff. Mirror the posting's words only where they are true.

AI engineer resumes
- Describe building and shipping AI applications (RAG, agents, voice, pipelines), not model training, unless that is true.
- Put AI keywords in the headline and summary: RAG, LLM agents, vector database, Gemini, Google Cloud.
- Never claim a tool or technique without work behind it. Hiring managers screen for evidence.

## Rules
(Paths are relative to the active tenant folder.)
- Only facts from `candidate-profile.md`, which also owns the truth whitelist and blacklist. Tailoring reorders bullets and rewrites the summary; it never adds a claim.
- Job titles, dates and employers match LinkedIn exactly. The headline under the name carries the target role.
- No em dashes. Run the checks below after every build.

## Build and check
```bash
python3 tools/make_resumes.py            # every config in the tenant's resume-content.json
python3 tools/make_resumes.py <config>   # one config from resume-content.json
python3 tools/make_resumes.py --new APP-052 --key acme --company Acme --headline "..." --summary "..." --record   # a new tailored variant
```
After building, extract the text from each PDF and confirm it reads in order, is two pages or fewer, and contains no em dashes or filler words.

## Choosing a resume
Pick the variant by role type. Each variant (a config in the tenant's `resume-content.json`) reorders the same true bullets.
| Role type | Lead with |
| --- | --- |
| The primary target role | The candidate's strongest real project of exactly that type |
| A neighbouring role (for example platform or full-stack versus applied AI) | The work that matches the posting's top requirements, in the posting's order |
| A front-end or full-stack role | The front-end work first (configuration suite, SIM platform front end), then the React parts of the AI projects; skills list starts with Front end. Build it from a copy of an existing front-end config |
| A stretch role | The honest closest evidence; never an invented claim. Say plainly what is applied versus research |

- Name the file `<Full_Name>_<Company>_Resume.pdf`. One tailored PDF per role type may be reused across companies.
- Record the PDF path in the `resume` field of the application entry in `data/applications.json`.
- Never use the resumes stored on LinkedIn (old front-end versions that may carry unverified claims).
- How to word AI years: see `candidate-profile.md`.
