# ATS playbook: form mechanics only

Per-system behaviour and BrowserOS neo tool quirks. Rules about what to answer live in `applicant-details.md` (standard answers, "Settled answers", "Learned answers") and `REQUIREMENTS.md` ("Ask the human"). Which company used which system is recorded in `data/applications.json`, not here.

## Habits that apply everywhere
- Reject non-essential cookies first. Teamtailor, Workday and others reload after the choice and wipe a half-filled form.
- Read the whole form back before submitting (`evaluate` or the review page) and report anything left empty.
- Required consents are ticked and logged in the company file. Optional marketing and SMS boxes stay unticked.
- The real office city comes from the company's own page; LinkedIn can be wrong.
- After submit, run `tools/record_application.py`.

## BrowserOS neo mechanics
- Refs from `snapshot` go stale after almost any edit. Re-run `grep` for fresh refs before each group of actions.
- `act kind=fill` types like a user. React forms (Ashby, Greenhouse) ignore values set from JavaScript even when they show on screen.
- Comboboxes: fill, then ArrowDown and Enter. Substring matching picks wrong options ("Man" selects "Woman"); for short or overlapping options open the list with `act click`, `grep` the option ref, click it, then read the value back. Enter does not always select (Greenhouse school and discipline need the option ref clicked).
- Mouse-event selection from `evaluate` (mousedown, mouseup, click) works for Google's custom dropdowns; plain `.click()` does not. Radios `act click` cannot reach can be clicked from `evaluate`.
- Uploads: `upload` needs the real `input[type=file]` ref. Greenhouse: the second "Attach". Ashby: make `#_systemfield_resume` visible, then `grep` its ref. Teamtailor: the "Upload CV" button. Lever: the resume button. Workday: make `input[type=file]` visible, then `grep`. Google: drag the PDF onto the drop zone with a `DataTransfer`, served from a local CORS server on port 18765 (stop it afterwards).
- Date spinbuttons (Workday MM/YYYY and similar) need the native value setter plus input and change events, or Tab from the previous field then `type` the digits. Clicking is blocked by an overlay. Screenshot to confirm.
- A button reported as "covered by" another element is behind a sticky footer or header: scroll first, then retry. Ashby submit and Next buttons are often under the sticky header. Last resort: focus the previous field, Tab, Enter.
- `evaluate` calls over about 60 seconds time out, and a navigation inside one raises "target navigated"; re-check state with a new call.

## Systems
- Greenhouse: embed form `https://job-boards.greenhouse.io/embed/job_app?for=<board>&token=<job id>`. Phone is a country-code box plus number. Location autocomplete: pick the exact city option, not a district or parish variant. Employment and education blocks can be required. reCAPTCHA is usually invisible; a visible tick box means hand over.
- Lever: `<job url>/apply`. Full name in one field, location autocomplete resolves to a "City, COUNTRYCODE" option, "previous employment" checkbox, demographic survey optional. hCaptcha was invisible.
- Ashby: `<job url>/application`. Location combobox (ArrowDown then Enter). Salary fields have no unit: enter the annual figure in the pay rule's currency and record the assumption. The date picker accepts typed MM/DD/YYYY. Buttons covered by the sticky header: scroll first.
- Teamtailor: `<job url>/applications/new`. Phone: use `type` into the field with the country selector; it normalises to the country format, so do not retype the prefix. Consent and work-permit radios. After submit it offers an optional survey and a "Connect" box: skip both. A first submit can fail on an empty phone field and a failed submit clears the file, so re-check the upload.
- Google Careers: signed in with the browser's Google account; profile first, multi-step. The resume parse is often wrong: fix school, degree, employers, dates and remove junk skill chips. Self-ID "Next" stays disabled until the consent box is ticked with a real click. Confirm the dashboard shows "Submitted".
- SmartRecruiters: Next and Submit report as covered. Click into the last text box, Tab, Enter (for Submit, Tab from the checkbox past Back, then Enter).
- Workday: needs a candidate account (hand over). Steps: My Information, My Experience, Application Questions, Voluntary Disclosures, Review; the portal then shows "In Review". Dropdowns: scroll so the option is clear of the footer, click, `grep` options, click the option; ArrowDown from "Select One" reaches the first real option.
- SuccessFactors: needs a candidate account (hand over).
- LinkedIn Easy Apply: the resume step uses a detached file input `upload` cannot address by ref, and stored LinkedIn resumes are old. Do not submit with a stored resume. Prefer "Apply on company website". Otherwise set blocker `upload` and hand over only that step. The upload CAN be done in a `run` script (worked for Tenth Revolution, 2026-10-23): click the "Upload resume" button, give the hidden `input[type=file]` an id with `page.evaluate`, resolve its node with `page.cdp('DOM.getDocument', {depth:-1, pierce:true})` then `DOM.querySelector`, and call `page.cdp('DOM.setFileInputFiles', {nodeId, files:[pdf]})`. The new file appears as a radio option; select it, then Next. Confirm in LinkedIn Job tracker > Applied. The upload also stays in the applicant's LinkedIn resume list.

## Add what you learn here
One row per finding, edited in place if a row already covers it.

| System | Behaviour | What works | Date |
| --- | --- | --- | --- |
| Workday | Resume autofill invents entries (a project became a job) and deleted entries are re-added from the draft; deleting does not stick | choose Apply Manually, upload the resume, leave work history empty; click real buttons, wait ~10s per step, reread Review before Submit. A stuck draft is deleted from Candidate Home, Actions menu | 2026-10-25 |
| Nordea SuccessFactors | Upload a Resume needs the small + icon, then 'Upload from Device' opens a native macOS picker (needs screen control; use Cmd+Shift+G and the full path). Dropdowns are paginated comboboxes: type does not filter, use arrow keys and Return with the mouse parked away. Apply button submits; required consent and screening questions appear after the first Apply click |  | 2026-10-25 |
| Teamtailor (Aira, TV4) | Application form can carry screening questions the ad lacks (Aira: '4 days per week in the office', years of product-driven work, EU/permanent-residency status) | open /applications/new and read the questions before deciding; Playwright can fill it without a sign-in; the CV upload goes through browser_file_upload after clicking Upload CV | 2026-10-28 |
| Ashby (G2) | Upload in the 'Autofill from resume' file input fills name, email, phone, location AND attaches the Resume field, and the number fields keep typed values; the optional 'contact me for up to 1080 days' consent is left unticked; success text 'Your application was successfully submitted' shows in place of the form |  | 2026-10-28 |
| Teamtailor (Tibber) | Phone field with +46 selected duplicates digits when filled then typed; clear it with the native value setter plus input event, then type 734026891 once. Dropdown menus stay open over radios: press Escape and click empty space. Submit redirects to /thanks (the 'Required' under Connect is the optional survey) |  | 2026-10-28 |
| LinkedIn jobs in BrowserOS neo | Job descriptions are not in innerText; the 'Apply on company website' link carries the real ATS URL (linkedin.com/safety/go/?url=...). Open that URL, wait about 2 seconds, then read. page.waitForSelector/waitForText can fail with 'not a function' inside run; use the wait tool |  | 2026-10-28 |

- Greenhouse react-select (Coinbase, Rubrik, Twilio, 2026-10-23): typing then Enter often does not commit; click the option by ref after a fresh snapshot. Typing "Male" lists Female too: click the option. Coinbase emails an 8-character security code to the applicant (read it from Gmail, enter it in the 8 boxes, resubmit). Coinbase and Rubrik need employment and education blocks or an NDA name; Twilio needs the AI Responsible Use Policy and demographic consent ticked.
