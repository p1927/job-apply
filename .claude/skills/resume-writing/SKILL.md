---
name: resume-writing
description: Write, tailor and render a resume that reads human, passes ATS parsing and looks designed. Use before writing or changing any resume, summary, bullet or skills list, and when choosing which skills to show for a role. Covers sounding human, ATS rules, layout, top skills by research, freelance work and the optional photo.
---

# Resume writing

Research dated 2026-11-22. Sources are at the bottom; most are vendor blogs, so treat the numbers as signals, not law. The truth rules in `CLAUDE.md` and the tenant's `candidate-profile.md` always win: never claim a skill, tool or number that is not stored. Ask the person once instead.

## 1. Sound human (Wikipedia "Signs of AI writing", via the community humanizer skill)
Remove these, then add specifics. Voiceless text is as obvious as slop.
- Puffed importance ("pivotal", "testament", "underscore", "showcase", "vibrant", "crucial", "fostering").
- Tacked-on "-ing" phrases ("...ensuring seamless delivery"). Split into two plain sentences.
- "serves as / boasts / features" for "is / has". "In order to" for "to".
- "Not just X, but Y", rule-of-three triplets, synonym cycling, false ranges ("from X to Y").
- Em dashes, curly quotes, emoji, bold on every phrase, "**Label:** text" lists in prose.
- Generic closers and anything that could describe any engineer. Copying the posting's sentences.
Add: one concrete detail per bullet (system, tool, size, constraint), short and long sentences mixed, plain verbs (built, wrote, moved, set up). Name one thing the person actually did.
Check: `python3 tools/check_resume_style.py` must print 0 problems, then read the result aloud.

## 2. ATS rules (tested: the built PDF must extract cleanly in reading order)
- One column. No tables, text boxes, icons, rating bars, skill graphics, or contact details in a header or footer.
- Arial or Helvetica body, 9.5 to 11 pt. No letter-spaced headings (they extract as "S U M M A RY"). Words must not extract one per line.
- Standard headings: Professional Summary, Professional Experience, Technical Skills, Projects, Education. Month and year on every date.
- Text-based PDF from Chrome. Test after every layout change: `pypdf` text extraction, check the order and that headings are whole words.
- Two pages at most. Never let a heading sit alone at the bottom of a page (the builder keeps headings with their content).
- Name the file `<Full_Name>_<Company>_Resume.pdf`.

## 3. Design (what `tools/make_resumes.py` renders)
Serif name, one accent colour (dark blue) on the role line and section headings, thin rules, dates aligned right, bold project names, a label column for skills, small grey contact line. Nothing decorative that a parser would read as text.
Photo: optional, off by default. US employers and most platforms prefer no photo, and a photo can trigger bias filters. Turn it on per config for markets where it is normal (`"photo": true` in the config, and `"photo": "<path inside the tenant folder>"` at the top of `resume-content.json`). It is a round 25 mm picture beside the name, embedded in the PDF, with empty alt text.

## 4. Skills to show (research)
- Huntr (121,788 postings, July 2026): most often required are Python 39%, JavaScript 36%, TypeScript 30%, Java 29%, problem-solving 23%. Docker, AWS, Kubernetes and Agile are more often "preferred". On resumes of people who reached interviews: Python, Git, TypeScript, JavaScript, Docker, SQL, PostgreSQL, CI/CD, GitHub Actions.
- Jobscan (10M job descriptions): top terms are engineering, design, computer science, programming, software development, JavaScript, Agile, testing. Resumes with a high match rate show Software Development, Python, JavaScript, SQL, GitHub.
- AI engineer roles (DataCamp, June 2026): Python and JavaScript, vector databases for RAG, prompt engineering, RAG, agentic AI with frameworks such as LangChain and LangGraph, cloud AI services (AWS, Azure, GCP), Docker and Kubernetes, MLOps and LLMOps (CI/CD, monitoring, cost and latency).
- Kickresume: name tools in the skills list (comma separated), then mention at least one in an experience bullet ("the skills section is for matching; the bullet is for credibility"). Group skills in categories. Drop buzzwords, proficiency bars and skills you barely know.
Use: lead with the languages and stack the posting names, mirror the posting's exact tool names only where true, keep the skills list to what the person can defend in an interview. Skills often on winning resumes that are NOT yet in a tenant's profile (Git, Docker, SQL, PostgreSQL, CI/CD, Kubernetes): ask the person which are true, then store them in `candidate-profile.md` before they appear on a resume.

## 4b. Freelance and client work (The Muse, Upwork, Jobscan, Resume Genius, Rezi)
- One line per project in a Projects section, or a single "Freelance" entry with selected projects when there are several. Label it as freelance, give the client's country or industry if the name is private, say what was built and the result.
- Chronological order. Only list projects that prove a skill the posting asks for; move the best one first.
- Use the stored wording from `candidate-profile.md` (for example the Opticalz client project: built in two weeks during vacations, for a client in India).

## 5. Fit to the posting
Read what the posting demands, then expand the matching stored facts (more detail, first in order). Do not paste its sentences. Rebuild with `python3 tools/make_resumes.py <config>`, run the style check, extract the PDF text and confirm the order.

## Sources
- https://github.com/c-b-g-m/blader-humanizer and https://raw.githubusercontent.com/davila7/claude-code-templates/HEAD/cli-tool/components/skills/productivity/humanizer/SKILL.md (24 patterns, from Wikipedia "Signs of AI writing")
- https://huntr.co/resume-skills/software-engineer
- https://www.jobscan.co/blog/resume-examples-keywords-for-software-engineers/
- https://www.datacamp.com/blog/essential-ai-engineer-skills
- https://www.kickresume.com/en/blog/best-ai-skills-to-put-on-your-resume/
- https://www.dice.com/career-advice/how-to-keep-an-ai-resume-from-hurting-your-job-hunt
- https://www.toptal.com/resume/career-center/how-to-write-a-tech-resume-for-software-engineering-roles
- https://www.themuse.com/advice/how-to-format-a-resume-with-freelance-work
