// Harvest every card of one LinkedIn results page in BrowserOS neo. Paste as the `code` of one `run` call after the
// tab has loaded (tabs action=new url=<search url> groupId=<group>, then run with page = that tab id).
// LinkedIn renders about 7 cards at a time, so this scrolls the results container in steps and accumulates.
// Returns TSV lines (id, company, title, location) for `python3 tools/coverage.py - --add --source linkedin`.
const p = browser.page(PAGE_ID);              // replace PAGE_ID
const acc = {};
const grab = async () => { const r = await p.evaluate(() => {
  const seen = [];
  document.querySelectorAll('a[href*="/jobs/view/"]').forEach(a => {
    const m = a.href.match(/jobs\/view\/(\d+)/); if (!m) return;
    const li = a.closest('li') || a.parentElement.parentElement;
    const t = (li ? li.innerText : a.innerText).split('\n').map(s => s.trim()).filter(Boolean);
    seen.push({ id: m[1], title: t[0], company: t[1], location: t[2] });
  });
  return seen; }); return r.value ?? r; };
for (let i = 0; i < 14; i++) {
  for (const it of await grab()) if (it.company) acc[it.id] = it;
  await p.evaluate(() => {
    let e = document.querySelector('a[href*="/jobs/view/"]');
    while (e && e !== document.body) { const s = getComputedStyle(e);
      if ((s.overflowY === 'auto' || s.overflowY === 'scroll') && e.scrollHeight > e.clientHeight + 50) { e.scrollTop += 500; return; }
      e = e.parentElement; }
    window.scrollBy(0, 500); });
  await sleep(700);
}
return Object.values(acc).map(x => [x.id, x.company, x.title, x.location].join('\t')).join('\n');
