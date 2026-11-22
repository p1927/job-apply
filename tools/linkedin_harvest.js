// Harvest every card of one LinkedIn results page in BrowserOS neo. Paste as the `code` of one `run` call after the
// tab has loaded (tabs action=new url=<search url> groupId=<group>, then run with page = that tab id).
// LinkedIn renders about 7 cards at a time, so this scrolls the results container in steps and accumulates.
// Returns TSV lines (id, company, title, location) for `python3 tools/coverage.py - --add --source linkedin`.
// Works on the old list layout (li cards with /jobs/view/ links) and the new one (div cards, currentJobId= links or data-job-id
// attributes). When nothing is found it returns a line starting HARVEST EMPTY with a probe of what the page contains.
const p = browser.page(PAGE_ID);              // replace PAGE_ID
const acc = {};
const grab = async () => { const r = await p.evaluate(() => {
  const out = [], seenIds = new Set();
  const idOf = (el) => {
    const h = el.getAttribute('href') || '';
    let m = h.match(/jobs\/view\/(\d+)/) || h.match(/currentJobId=(\d+)/);
    if (m) return m[1];
    for (let n = el; n && n !== document.body; n = n.parentElement) {   // data attributes on the card
      const v = n.getAttribute('data-occludable-job-id') || n.getAttribute('data-job-id') ||
                (n.getAttribute('data-entity-urn') || '').replace(/\D/g, '');
      if (v && v.length >= 6) return v;
    }
    return null;
  };
  const cards = new Set();
  document.querySelectorAll('a[href*="/jobs/view/"], a[href*="currentJobId="], [data-occludable-job-id], [data-job-id]')
    .forEach(a => cards.add(a));
  cards.forEach(a => {
    const id = idOf(a); if (!id || seenIds.has(id)) return; seenIds.add(id);
    const card = a.closest('[data-occludable-job-id], [data-job-id], li, [role="listitem"], div[componentkey]') ||
                 a.parentElement?.parentElement || a;
    const lines = (card.innerText || a.innerText || '').split('\n').map(s => s.trim()).filter(Boolean)
      .filter(s => !/^(promoted|viewed|easy apply|actively recruiting|be an early applicant|\d+ (day|week|hour|month)s? ago|new)$/i.test(s));
    if (lines.length >= 2) out.push({ id, title: lines[0], company: lines[1], location: lines[2] || '' });
  });
  return { cards: out, probe: { viewLinks: document.querySelectorAll('a[href*="/jobs/view/"]').length,
                                currentJobId: document.querySelectorAll('a[href*="currentJobId="]').length,
                                dataIds: document.querySelectorAll('[data-occludable-job-id],[data-job-id]').length,
                                url: location.href, title: document.title } };
}); return r.value ?? r; };
let probe = null;
for (let i = 0; i < 14; i++) {
  const g = await grab(); probe = g.probe;
  for (const it of g.cards) acc[it.id] = it;
  await p.evaluate(() => {
    let e = document.querySelector('a[href*="/jobs/view/"], [data-occludable-job-id], [data-job-id]');
    while (e && e !== document.body) { const s = getComputedStyle(e);
      if ((s.overflowY === 'auto' || s.overflowY === 'scroll') && e.scrollHeight > e.clientHeight + 50) { e.scrollTop += 500; return; }
      e = e.parentElement; }
    window.scrollBy(0, 500); });
  await sleep(700);
}
const rows = Object.values(acc).map(x => [x.id, x.company, x.title, x.location].join('\t'));
if (!rows.length) return 'HARVEST EMPTY. probe=' + JSON.stringify(probe) +
  ' (not logged in, login wall, or a new layout: send this probe line to Claude, do not report zero jobs)';
return rows.join('\n');
