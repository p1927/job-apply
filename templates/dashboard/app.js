/* Job search dashboard (read-only). State comes from /api/state; /events says when a file changed. No libraries, no network beyond localhost. */
(() => {
'use strict';
const TOKEN = document.body.dataset.token;
const $ = (s, r = document) => r.querySelector(s);
const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const enc = encodeURIComponent;

/* ---------- icons ---------- */
const ICON = {
  home:'<path d="M3 11l9-8 9 8"/><path d="M5 10v10h14V10"/>',
  brief:'<rect x="3" y="7" width="18" height="13" rx="2"/><path d="M9 7V5a2 2 0 012-2h2a2 2 0 012 2v2M3 13h18"/>',
  search:'<circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/>',
  target:'<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>',
  file:'<path d="M14 3H7a2 2 0 00-2 2v14a2 2 0 002 2h10a2 2 0 002-2V8z"/><path d="M14 3v5h5M9 13h6M9 17h6"/>',
  user:'<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0116 0"/>',
  check:'<path d="M20 6L9 17l-5-5"/>', alert:'<path d="M12 3l10 18H2z"/><path d="M12 10v5M12 18v.01"/>',
  x:'<path d="M18 6L6 18M6 6l12 12"/>', help:'<circle cx="12" cy="12" r="9"/><path d="M9.5 9a2.5 2.5 0 015 .5c0 1.7-2.5 2-2.5 3.5M12 17v.01"/>',
  link:'<path d="M10 13a5 5 0 007 0l3-3a5 5 0 00-7-7l-1 1"/><path d="M14 11a5 5 0 00-7 0l-3 3a5 5 0 007 7l1-1"/>',
  send:'<path d="M22 2L11 13M22 2l-7 20-4-9-9-4z"/>', sun:'<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
  moon:'<path d="M21 13A9 9 0 1111 3a7 7 0 0010 10z"/>', auto:'<circle cx="12" cy="12" r="9"/><path d="M12 3v18"/><path d="M12 3a9 9 0 010 18" fill="currentColor"/>',
  ext:'<path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 01-1 1H5a1 1 0 01-1-1V7a1 1 0 011-1h5"/>', spark:'<path d="M12 3l2 6 6 2-6 2-2 6-2-6-6-2 6-2z"/>'
};
const ico = n => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICON[n] || ''}</svg>`;

/* ---------- words ---------- */
const REASON = {'wrong-role':'Wrong kind of role','not-ai':'Not an AI role','swe-secondary':'Plain software role','location':'Wrong location','on-site':'Too many office days',
  'consultancy':'Consultancy','staffing':'Staffing or outsourcing','manager':'People-manager role','contract':'Contract only','startup':'Early-stage startup','language':'Language required',
  'clearance':'Security clearance','low-pay':'Pay below minimum','seniority':'Wrong seniority','research':'Research role','duplicate':'Duplicate','already-applied':'Already applied',
  'posting-gone':'Posting removed','other':'Other reason'};
const LSTATUS = {New:'To review', Relevant:'Good fit', 'Not-relevant':'Skipped', Applied:'Applied', Closed:'Closed'};
const BLOCKER = {captcha:'A CAPTCHA needs you', account:'An account or login is needed', upload:'A file upload needs you', fact:'A fact only you know', other:'Needs your input'};
const reason = c => REASON[c] || c || '';
const lstat = s => LSTATUS[s] || s;
const ACTIVE = ['Applied', 'Screening', 'Interview', 'Offer'];
const CLOSED = ['Rejected', 'Withdrawn', 'Dropped'];
const STEPS = [
  ['Found and checked against your requirements', 'Claude'],
  ['Tailored resume built', 'Claude'],
  ['Approved to apply', 'You, or your standing approval'],
  ['Application submitted', 'Claude'],
  ['Confirmation and every answer saved', 'Claude, in the application file'],
  ['Follow-up check', 'Claude checks the status; any message to a recruiter needs your OK'],
  ['Recruiter screen', 'You'],
  ['Interviews', 'You, with Claude helping you prepare'],
  ['Offer', 'Negotiate toward your target pay']
];

/* ---------- helpers ---------- */
const MON = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
function fdate(d){
  const m = /^(\d{4})-(\d\d)-(\d\d)/.exec(d || ''); if (!m) return d || '';
  const same = S && S.today && S.today.slice(0, 4) === m[1];
  return +m[3] + ' ' + MON[+m[2] - 1] + (same ? '' : ' ' + m[1]);
}
const fileUrl = p => '/api/file?path=' + enc(p);
const base = p => (p || '').split('/').pop();
const pill = s => `<span class="pill ${esc(s)}">${esc(s)}</span>`;
const lpill = s => `<span class="pill ${esc(s)}">${esc(lstat(s))}</span>`;
function chk(k){
  const ic = {pass:'check', warn:'alert', fail:'x', unknown:'help'}[k.s] || 'help';
  return `<span class="chk ${esc(k.s)}" title="${esc(k.k + ': ' + k.n)}">${ico(ic)}${esc(k.k)}</span>`;
}
function fuBadge(a){
  if (!a.fu) return '';
  const t = a.fu.state === 'overdue' ? 'Follow-up overdue since ' : a.fu.state === 'due' ? 'Follow-up due today' : 'Follow-up ';
  return `<span class="fu ${a.fu.state}">${t}${a.fu.state === 'due' ? '' : esc(fdate(a.fu.date))}</span>`;
}
const flashed = new Set();
const fl = k => flashed.has(k) ? ' flash' : '';

/* ---------- markdown (small, safe: everything is escaped first) ---------- */
function mdLink(t, u){
  const raw = u.replace(/&amp;/g, '&');
  if (/^https?:\/\//i.test(raw)) return `<a href="${u}" target="_blank" rel="noopener noreferrer">${t}</a>`;
  const rel = raw.replace(/^\.?\/+/, '').replace(/\.\.\//g, '');
  if (/\.(md|pdf|json|csv|txt)$/i.test(rel)) return `<a href="${fileUrl(rel)}" target="_blank" rel="noopener">${t}</a>`;
  return t;
}
function inline(s){
  s = esc(s);
  const codes = [];
  s = s.replace(/`([^`]+)`/g, (m, c) => { codes.push(c); return '\u0000' + (codes.length - 1) + '\u0000'; });
  s = s.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>').replace(/(^|[^*\w])\*([^*\s][^*]*?)\*(?!\*)/g, '$1<em>$2</em>');
  s = s.replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, (m, t, u) => mdLink(t, u));
  s = s.replace(/(^|[\s(])(https?:\/\/[^\s<)]+)/g, (m, a, u) => `${a}<a href="${u}" target="_blank" rel="noopener noreferrer">${u}</a>`);
  return s.replace(/\u0000(\d+)\u0000/g, (m, i) => '<code>' + codes[+i] + '</code>');
}
function md(text){
  const L = String(text || '').replace(/\r/g, '').split('\n'), out = [];
  let i = 0;
  const cells = l => l.trim().replace(/^\||\|$/g, '').split(/(?<!\\)\|/).map(c => c.replace(/\\\|/g, '|').trim());
  while (i < L.length){
    const l = L[i];
    if (/^```/.test(l)){ const b = []; i++; while (i < L.length && !/^```/.test(L[i])) b.push(L[i++]); i++; out.push('<pre><code>' + esc(b.join('\n')) + '</code></pre>'); continue; }
    if (!l.trim()){ i++; continue; }
    let m = /^(#{1,4})\s+(.*)$/.exec(l);
    if (m){ out.push(`<h${m[1].length}>${inline(m[2])}</h${m[1].length}>`); i++; continue; }
    if (/^\s*([-*_]\s*){3,}$/.test(l)){ out.push('<hr>'); i++; continue; }
    if (/^\s*\|/.test(l) && /^\s*\|?\s*:?-{2,}/.test(L[i + 1] || '')){
      const head = cells(l); i += 2; const rows = [];
      while (i < L.length && /^\s*\|/.test(L[i])) rows.push(cells(L[i++]));
      out.push('<table><thead><tr>' + head.map(c => `<th>${inline(c)}</th>`).join('') + '</tr></thead><tbody>' +
        rows.map(r => '<tr>' + head.map((_, j) => `<td>${inline(r[j] || '')}</td>`).join('') + '</tr>').join('') + '</tbody></table>');
      continue;
    }
    if (/^>\s?/.test(l)){ const b = []; while (i < L.length && /^>\s?/.test(L[i])) b.push(L[i++].replace(/^>\s?/, '')); out.push('<blockquote>' + inline(b.join(' ')) + '</blockquote>'); continue; }
    if (/^\s*([-*]|\d+\.)\s+/.test(l)){
      const ordered = /^\s*\d+\./.test(l), items = [];
      while (i < L.length && /^\s*([-*]|\d+\.)\s+/.test(L[i])){
        const mm = /^(\s*)([-*]|\d+\.)\s+(.*)$/.exec(L[i++]); let txt = mm[3];
        while (i < L.length && L[i].trim() && /^\s{2,}\S/.test(L[i]) && !/^\s*([-*]|\d+\.)\s+/.test(L[i])) txt += ' ' + L[i++].trim();
        items.push(`<li style="margin-left:${Math.min(3, Math.floor(mm[1].length / 2)) * 16}px">${inline(txt)}</li>`);
      }
      out.push((ordered ? '<ol>' : '<ul>') + items.join('') + (ordered ? '</ol>' : '</ul>'));
      continue;
    }
    const p = [];
    while (i < L.length && L[i].trim() && !/^(#{1,4}\s|```|>|\s*\|)/.test(L[i]) && !/^\s*([-*]|\d+\.)\s+/.test(L[i])) p.push(L[i++].trim());
    if (!p.length){ p.push(L[i++]); }
    out.push('<p>' + inline(p.join(' ')) + '</p>');
  }
  return '<div class="md">' + out.join('') + '</div>';
}

/* ---------- state ---------- */
let S = null, lastUpdate = null;
const files = {};
const ui = {aStatus:'', aTrack:'', aView:'board', aQ:'', jStatus:'', jCat:'', jReason:'', jQ:'', jLimit:100, tab:'summary', resume:'', fill:''};
const route = () => {
  const h = (location.hash || '#/overview').slice(2), [path, q] = h.split('?');
  return {view: path || 'overview', app: new URLSearchParams(q || '').get('app') || ''};
};
const go = (view, app) => { location.hash = '#/' + view + (app ? '?app=' + enc(app) : ''); };
const appById = id => S && S.apps.find(a => a.id === id);

/* ---------- views ---------- */
const NAV = [['overview','Overview','home'], ['apps','Applications','brief'], ['jobs','Jobs found','search'], ['requirements','Requirements','target'], ['resumes','Resumes','file'], ['profile','About you','user']];

function header(title, sub, right){
  return `<div class="ph"><div><h1>${esc(title)}</h1>${sub ? `<p>${sub}</p>` : ''}</div>${right ? `<div class="right">${right}</div>` : ''}</div>`;
}
function bars(rows, max){
  return '<div class="hbars">' + rows.map(([l, v, hint]) => `<div class="hbar"><span title="${esc(l)}" style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(l)}</span><span class="bar"><i style="width:${max ? Math.max(2, v / max * 100) : 0}%"></i></span><span class="val">${v}</span></div>`).join('') + '</div>';
}

function vOverview(){
  const A = S.apps, Lg = S.ledger;
  const open = A.filter(a => ACTIVE.includes(a.status)), talking = A.filter(a => ['Screening','Interview','Offer'].includes(a.status));
  const fuDue = A.filter(a => a.fu && a.fu.state !== 'upcoming'), nNew = Lg.filter(r => r.status === 'New').length;
  const nextFu = A.filter(a => a.fu && a.fu.state === 'upcoming').sort((x, y) => x.fu.date.localeCompare(y.fu.date))[0];
  let h = header((S.tenant.name || 'Your') + (S.tenant.name ? "'s job search" : ' job search'), `Everything Claude has found and done, live from your files. Today is ${esc(fdate(S.today))}.`);

  if (S.needs.length){
    h += `<div class="needs">${ico('alert')}<div><b>${S.needs.length} ${S.needs.length === 1 ? 'thing needs' : 'things need'} you</b><ul>` +
      S.needs.map(n => `<li><b>${esc(n.company)}</b> ${esc(n.title)} <span class="muted">${esc(BLOCKER[n.blocker] || n.blocker)}</span>${n.app ? ` <a href="#" data-app="${esc(n.app)}">Open</a>` : ''}</li>`).join('') + '</ul></div></div>';
  } else {
    h += `<div class="needs clear">${ico('check')}<div><b>Nothing is waiting on you</b><span class="muted">Claude will pause and show it here when it needs a CAPTCHA, a login or a fact only you know.</span></div></div>`;
  }

  const kpi = (v, l, s, href) => `<a class="card kpi" href="${href}"><span class="v">${v}</span><span class="l">${l}</span><span class="s">${s}</span></a>`;
  h += '<div class="grid g4" style="margin-bottom:14px">' +
    kpi(open.length, 'Open applications', `${A.filter(a => a.dateApplied).length} applied in total`, '#/apps') +
    kpi(talking.length, 'In conversation', talking.length ? esc(talking.map(a => a.company).slice(0, 2).join(', ')) : 'Screens, interviews, offers', '#/apps') +
    kpi(fuDue.length, 'Follow-ups due', fuDue.length ? 'Overdue or due today' : nextFu ? 'Next on ' + esc(fdate(nextFu.fu.date)) : 'None scheduled', '#/apps') +
    kpi(Lg.length, 'Jobs seen', nNew ? nNew + ' still to review' : 'All reviewed', '#/jobs') + '</div>';

  const passed = Math.max(Lg.filter(r => ['Relevant','Applied'].includes(r.status)).length, A.filter(a => a.dateApplied).length);
  const applied = A.filter(a => a.dateApplied).length;
  const heard = A.filter(a => a.dateApplied && ['Screening','Interview','Offer','Rejected'].includes(a.status)).length;
  const deep = A.filter(a => ['Interview','Offer'].includes(a.status)).length;
  const stages = [['Jobs seen', Lg.length], ['Passed your rules', passed], ['Applied', applied], ['Heard back', heard], ['Interview or offer', deep]];
  const top = Math.max(1, stages[0][1]);
  const funnel = '<div class="fun">' + stages.map(([l, v], i) => `<div class="fun-row"><span>${l}</span><span class="bar"><i style="width:${v / top * 100}%;background:var(--f${i + 1})"></i></span><span class="val">${v} <small>${i ? Math.round(v / top * 100) + '%' : ''}</small></span></div>`).join('') + '</div>';

  const skip = {};
  Lg.filter(r => r.status === 'Not-relevant').forEach(r => { const k = reason(r.reason) || 'No reason recorded'; skip[k] = (skip[k] || 0) + 1; });
  let sk = Object.entries(skip).sort((a, b) => b[1] - a[1]);
  if (sk.length > 8){ const rest = sk.slice(7).reduce((s, x) => s + x[1], 0); sk = sk.slice(0, 7).concat([['Everything else', rest]]); }
  const skipped = Lg.filter(r => r.status === 'Not-relevant').length;

  const fus = A.filter(a => a.fu).sort((x, y) => x.fu.date.localeCompare(y.fu.date));
  const fuHtml = fus.length ? '<div class="list">' + fus.slice(0, 6).map(a => `<div class="li" role="button" tabindex="0" data-app="${esc(a.id)}"><div class="grow"><div class="t">${esc(a.company)}</div><div class="muted">${esc(a.role)}</div></div>${fuBadge(a)}</div>`).join('') + '</div>'
    : '<div class="empty"><b>No follow-ups scheduled</b>Claude checks your inbox for replies once something is applied.</div>';

  const ev = [];
  A.forEach(a => {
    if (a.dateApplied) ev.push({d: a.dateApplied, k: 'applied', a, t: `Applied to <b>${esc(a.company)}</b>`});
    if (a.dateFound && a.status !== 'Dropped') ev.push({d: a.dateFound, k: 'found', a, t: `Found <b>${esc(a.company)}</b>, ${esc(a.role)}`});
    if (a.followUp && a.followUp.lastCheck) ev.push({d: a.followUp.lastCheck, k: 'check', a, t: `Checked for a reply from <b>${esc(a.company)}</b>`});
  });
  ev.sort((x, y) => y.d.localeCompare(x.d));
  const evHtml = ev.length ? ev.slice(0, 10).map(e => `<div class="act${fl('a:' + e.a.id)}" role="button" tabindex="0" data-app="${esc(e.a.id)}"><time>${esc(fdate(e.d))}</time><span class="dot ${e.k}"></span><span>${e.t}</span></div>`).join('')
    : '<div class="empty"><b>No activity yet</b>Applications and checks show up here as they happen.</div>';

  h += '<div class="grid g21"><div class="stack">' +
    `<section class="card pad"><h3>From first sight to offer</h3>${funnel}</section>` +
    `<section class="card pad"><h3>Why jobs were skipped <span class="faint">(${skipped})</span></h3>${sk.length ? bars(sk, sk[0][1]) : '<div class="empty">Nothing skipped yet.</div>'}</section>` +
    '</div><div class="stack">' +
    `<section class="card pad"><h3>Follow-ups</h3>${fuHtml}</section>` +
    `<section class="card pad"><h3>Recent activity</h3>${evHtml}</section></div></div>`;
  return h;
}

function appRow(a){
  const resume = a.resume ? `<span class="tag" title="${esc(a.resume)}">${ico('file').replace('<svg', '<svg width="11" height="11"')} Resume</span>` : '';
  return `<tr class="click${CLOSED.includes(a.status) ? ' dim' : ''}${fl('a:' + a.id)}" tabindex="0" data-app="${esc(a.id)}">
    <td><div class="co">${esc(a.company)}</div><div class="sub">${esc(a.role)}</div><div class="row-chips" style="margin-top:5px">${a.bigTech ? '<span class="tag big">Big tech</span>' : ''}<span class="tag">${esc(a.id)}</span>${a.tag ? `<span class="tag">${esc(a.tag)}</span>` : ''}</div></td>
    <td>${pill(a.status)}${a.fu ? '<div style="margin-top:6px">' + fuBadge(a) + '</div>' : ''}${a.blocker ? `<div style="margin-top:6px"><span class="fu due">Needs you: ${esc(BLOCKER[a.blocker] || a.blocker)}</span></div>` : ''}</td>
    <td class="hide-sm"><div>${esc(a.location)}</div><div class="sub">${esc(a.mode)}</div></td>
    <td class="hide-sm"><div class="pay">${esc(a.pay)}</div></td>
    <td><div class="row-chips">${a.checks.map(chk).join('')}</div></td>
    <td class="hide-sm"><div>${a.dateApplied ? esc(fdate(a.dateApplied)) : '<span class="faint">Not applied</span>'}</div><div style="margin-top:5px">${resume}</div></td></tr>`;
}
function kCard(a){
  return `<div class="kcard${fl('a:' + a.id)}" role="button" tabindex="0" data-app="${esc(a.id)}"><b>${esc(a.company)}</b><span class="r">${esc(a.role)}</span>
    <div class="row-chips">${a.checks.map(chk).join('')}</div>
    <div class="meta">${a.bigTech ? '<span class="tag big">Big tech</span>' : ''}<span>${esc(a.location)}</span>${a.dateApplied ? '<span>· applied ' + esc(fdate(a.dateApplied)) + '</span>' : ''}${fuBadge(a)}</div></div>`;
}
function vApps(){
  const q = ui.aQ.toLowerCase();
  const list = S.apps.filter(a => (!ui.aStatus || a.status === ui.aStatus) && (!ui.aTrack || a.track === ui.aTrack) && (!q || (a.company + ' ' + a.role + ' ' + a.id).toLowerCase().includes(q)));
  let h = header('Applications', 'Every role Claude shortlisted or applied to. Click one for its full story.',
    `<div class="seg" role="group" aria-label="View"><button data-set="aView=board" aria-pressed="${ui.aView === 'board'}">Board</button><button data-set="aView=list" aria-pressed="${ui.aView === 'list'}">List</button></div>`);
  const order = S.vocab.appOrder;
  h += '<div class="bar-row"><div class="seg" role="group" aria-label="Filter by status"><button data-set="aStatus=" aria-pressed="' + !ui.aStatus + '">All<span class="n">' + S.apps.length + '</span></button>' +
    order.map(s => `<button data-set="aStatus=${esc(s)}" aria-pressed="${ui.aStatus === s}">${esc(s)}<span class="n">${S.apps.filter(a => a.status === s).length}</span></button>`).join('') + '</div>' +
    `<label class="search">${ico('search')}<input id="aQ" data-in="aQ" type="search" placeholder="Company or role" value="${esc(ui.aQ)}" aria-label="Search applications"></label>` +
    `<select data-in="aTrack" aria-label="Track"><option value="">All tracks</option>${S.tracks.map(t => `<option value="${esc(t[0])}"${ui.aTrack === t[0] ? ' selected' : ''}>${esc(t[1])}</option>`).join('')}</select>` +
    `<span class="count">${list.length} of ${S.apps.length}</span></div>`;
  if (!list.length) return h + '<div class="card empty"><b>No applications match</b>Try clearing a filter.</div>';
  if (ui.aView === 'board'){
    const cols = ['Shortlisted','Applied','Screening','Interview','Offer'].filter(s => order.includes(s)).map(s => [s, list.filter(a => a.status === s)]);
    cols.push(['Closed', list.filter(a => CLOSED.includes(a.status))]);
    h += '<div class="kan">' + cols.map(([s, items]) => `<div class="kcol"><h4><span>${esc(s)}</span><span class="num">${items.length}</span></h4>${items.map(kCard).join('') || '<div class="faint" style="padding:6px 4px;font-size:13px">Nothing here</div>'}</div>`).join('') + '</div>';
    return h;
  }
  S.tracks.forEach(([key, name]) => {
    const items = list.filter(a => a.track === key).sort((x, y) => CLOSED.includes(x.status) - CLOSED.includes(y.status) || order.indexOf(y.status) - order.indexOf(x.status));
    if (!items.length) return;
    h += `<div class="group-h">${esc(name)} <span class="num">${items.length}</span></div><div class="card wrap-x"><table class="tbl"><thead><tr><th>Company and role</th><th>Status</th><th class="hide-sm">Where</th><th class="hide-sm">Pay</th><th>Requirement checks</th><th class="hide-sm">Applied</th></tr></thead><tbody>${items.map(appRow).join('')}</tbody></table></div>`;
  });
  return h;
}

function vJobs(){
  const Lg = S.ledger, q = ui.jQ.toLowerCase();
  const cats = [...new Set(Lg.map(r => r.category).filter(Boolean))].sort();
  const reasons = [...new Set(Lg.map(r => r.reason).filter(Boolean))].sort((a, b) => reason(a).localeCompare(reason(b)));
  const rank = s => ({Relevant: 0, New: 1, Applied: 2, 'Not-relevant': 3, Closed: 4})[s] ?? 5;
  const list = Lg.filter(r => (!ui.jStatus || r.status === ui.jStatus) && (!ui.jCat || r.category === ui.jCat) && (!ui.jReason || r.reason === ui.jReason) &&
    (!q || (r.company + ' ' + r.title + ' ' + r.location + ' ' + r.note).toLowerCase().includes(q)))
    .sort((a, b) => rank(a.status) - rank(b.status) || a.company.localeCompare(b.company));
  const stat = ['', ...S.vocab.ledgerStatus.filter(s => Lg.some(r => r.status === s))];
  let h = header('Jobs found', 'Every posting Claude has looked at, and what it decided about each one.');
  h += '<div class="bar-row"><div class="seg" role="group" aria-label="Filter by status">' + stat.map(s => `<button data-set="jStatus=${esc(s)}" aria-pressed="${ui.jStatus === s}">${s ? esc(lstat(s)) : 'All'}<span class="n">${s ? Lg.filter(r => r.status === s).length : Lg.length}</span></button>`).join('') + '</div>' +
    `<label class="search">${ico('search')}<input id="jQ" data-in="jQ" type="search" placeholder="Company, title, place" value="${esc(ui.jQ)}" aria-label="Search jobs"></label>` +
    `<select data-in="jCat" aria-label="Category"><option value="">All categories</option>${cats.map(c => `<option value="${esc(c)}"${ui.jCat === c ? ' selected' : ''}>${esc(S.vocab.categoryNotes[c] ? c + ': ' + S.vocab.categoryNotes[c] : c)}</option>`).join('')}</select>` +
    `<select data-in="jReason" aria-label="Reason"><option value="">All reasons</option>${reasons.map(c => `<option value="${esc(c)}"${ui.jReason === c ? ' selected' : ''}>${esc(reason(c))}</option>`).join('')}</select>` +
    `<span class="count">${list.length} of ${Lg.length}</span></div>`;
  if (!list.length) return h + '<div class="card empty"><b>No jobs match</b>Try clearing a filter.</div>';
  const rows = list.slice(0, ui.jLimit).map(r => {
    const app = r.app_id && appById(r.app_id);
    const why = r.reason ? `<div><b>${esc(reason(r.reason))}</b></div>` : '';
    const act = app ? `<a href="#" class="btn sm" data-app="${esc(app.id)}">${esc(app.id)}</a>` :
      r.status === 'Relevant' ? `<button class="btn sm" type="button" data-ask="Apply to ${esc(r.company)}, ${esc(r.title)} (job ${esc(r.job_id)}), if it passes my requirements." data-ctx="${esc(r.company)}">Ask Claude to apply</button>` : '';
    return `<tr class="${r.status === 'Not-relevant' ? 'dim' : ''}${fl('j:' + r.job_id)}"><td><div class="co">${esc(r.company)}</div><div class="sub">${esc(r.title)}</div></td>
      <td>${lpill(r.status)}</td><td class="hide-sm"><div>${esc(r.location)}</div><div class="sub">${esc(r.workplace)}</div></td>
      <td>${why}<div class="sub">${esc(r.note)}</div>${r.blocker ? `<div><span class="fu due">Needs you: ${esc(BLOCKER[r.blocker] || r.blocker)}</span></div>` : ''}</td>
      <td class="hide-sm"><span class="tag">${esc(r.category)}</span><div class="sub" style="margin-top:4px">${esc(r.source)}</div></td><td>${act}</td></tr>`;
  }).join('');
  h += `<div class="card wrap-x"><table class="tbl"><thead><tr><th>Company and title</th><th>Decision</th><th class="hide-sm">Where</th><th>Why</th><th class="hide-sm">Category</th><th></th></tr></thead><tbody>${rows}</tbody></table></div>`;
  if (list.length > ui.jLimit) h += `<p style="text-align:center;margin-top:14px"><button class="btn" data-more="1">Show ${Math.min(100, list.length - ui.jLimit)} more</button></p>`;
  return h;
}

function vRequirements(){
  const R = S.requirements, sum = S.requirementSummary, labels = Object.keys(S.requirementLabels).length ? S.requirementLabels : null;
  let h = header('Your requirements', 'The rules every role is measured against. Change them by telling Claude, below.',
    '<button class="btn" type="button" data-ask="I want to change a requirement.">Ask Claude to change this</button>');
  const keys = labels ? Object.keys(labels).filter(k => sum[k]) : Object.keys(sum);
  if (keys.length) h += '<dl class="glance">' + keys.map(k => `<div><dt>${esc(labels ? labels[k] : k)}</dt><dd>${esc(sum[k])}</dd></div>`).join('') + '</dl>';
  const checks = {};
  S.apps.filter(a => a.status !== 'Dropped').forEach(a => a.checks.forEach(c => { (checks[c.k] = checks[c.k] || {pass:0, warn:0, fail:0, unknown:0})[c.s] = ((checks[c.k] || {})[c.s] || 0) + 1; }));
  const ck = Object.entries(checks);
  if (ck.length) h += `<section class="card pad" style="margin-bottom:14px"><h3>How the roles Claude shortlisted measured up</h3><div class="hbars">` +
    ck.map(([k, c]) => { const t = c.pass + c.warn + c.fail + c.unknown; return `<div class="hbar" style="grid-template-columns:90px minmax(0,1fr) 120px"><span>${esc(k)}</span><span class="stk" role="img" aria-label="${esc(k)}: ${c.pass} pass, ${c.warn} partly, ${c.fail} fail, ${c.unknown} unknown">${['pass','warn','fail','unknown'].filter(s => c[s]).map(s => `<i class="${s}" style="flex:${c[s]}"></i>`).join('')}</span><span class="faint" style="font-size:12px">${c.pass} of ${t} pass</span></div>`; }).join('') +
    `</div><div class="legend"><span style="--c:var(--good)">Pass</span><span style="--c:#d19a1f">Partly or open</span><span style="--c:var(--bad)">Fails</span><span style="--c:var(--ink3)">Unknown</span></div></section>`;
  if (!R.sections.length && !R.intro) return h + '<div class="card empty"><b>No requirements written yet</b>Tell Claude what you are looking for and it will record it here.</div>';
  const intro = R.intro.replace(/^#.*\n?/, '').trim();
  if (intro) h += `<div class="card pad" style="margin-bottom:14px">${md(intro)}</div>`;
  h += '<div class="req-grid">' + R.sections.map(s => `<section class="card"><h3>${esc(s.title)}</h3>${md(s.body)}</section>`).join('') + '</div>';
  return h;
}

function vResumes(){
  const items = [];
  S.baseResumes.forEach(p => items.push({path: p, title: p.endsWith('.pdf') ? 'Base resume' : 'Base resume (text)', sub: base(p), status: ''}));
  S.apps.filter(a => a.resume && !a.resumeMissing).forEach(a => items.push({path: a.resume, title: a.company, sub: a.role, status: a.status, id: a.id}));
  let h = header('Resumes', 'The base resume and every version Claude tailored, with the role it was used for.');
  if (!items.length) return h + '<div class="card empty"><b>No resumes yet</b>Claude builds one for each application.</div>';
  const cur = items.find(i => i.path === ui.resume) || items[0];
  const preview = cur.path.endsWith('.pdf') ? `<iframe src="${fileUrl(cur.path)}#view=FitH" title="${esc(cur.title)} resume"></iframe>` : fileBox(cur.path);
  h += '<div class="res-layout"><div class="card">' + items.map(i => `<button type="button" class="res-item" data-set="resume=${esc(i.path)}" aria-pressed="${i.path === cur.path}">${ico('file')}<span class="grow"><div><b>${esc(i.title)}</b></div><div class="muted">${esc(i.sub)}</div></span>${i.status ? pill(i.status) : ''}</button>`).join('') + '</div>' +
    `<div class="preview"><div class="bar-row"><b>${esc(base(cur.path))}</b>${cur.id ? `<a href="#" class="btn sm" data-app="${esc(cur.id)}">Open application</a>` : ''}<a class="btn sm" href="${fileUrl(cur.path)}" target="_blank" rel="noopener">${ico('ext')}Open in a new tab</a></div>${preview}</div></div>`;
  return h;
}
function fileBox(path){
  loadFile(path);
  const f = files[path];
  return f && f.text != null ? `<div class="card">${md(f.text)}</div>` : '<div class="card empty">Loading</div>';
}
function vProfile(){
  let h = header('About you', 'The facts Claude is allowed to use in resumes and answers. Nothing outside this list is ever claimed.', '<button class="btn" type="button" data-ask="Please update a fact in my profile.">Ask Claude to update this</button>');
  return h + (S.profile.trim() ? `<div class="card pad">${md(S.profile)}</div>` : '<div class="card empty"><b>No profile yet</b>Claude builds this during setup.</div>');
}
const VIEWS = {overview: vOverview, apps: vApps, jobs: vJobs, requirements: vRequirements, resumes: vResumes, profile: vProfile};

/* ---------- drawer ---------- */
function journey(a){
  const fu = a.fu ? fdate(a.fu.date) : '';
  const mk = (i, state) => ({t: STEPS[i][0], w: STEPS[i][1] + (i === 5 && fu ? ' (' + fu + ')' : ''), state});
  if (a.status === 'Dropped') return [mk(0, 'done'), {t: 'Decided not to apply', w: a.notes || 'It did not fit your rules', state: 'skip'}];
  if (a.status === 'Rejected' || a.status === 'Withdrawn'){
    const n = a.dateApplied ? 5 : 1;
    return STEPS.slice(0, n).map((_, i) => mk(i, 'done')).concat([{t: a.status === 'Rejected' ? 'Rejected by the company' : 'Withdrawn', w: a.notes || '', state: 'skip'}]);
  }
  const done = {Shortlisted: a.resume ? 2 : 1, Applied: 5, Screening: 6, Interview: 7, Offer: 8}[a.status] || 1;
  return STEPS.map((_, i) => mk(i, i < done ? 'done' : i === done ? 'now' : 'todo'));
}
function dSummary(a){
  let h = '';
  const failing = a.checks.filter(c => c.s === 'fail');
  if (a.blocker) h += `<div class="callout warn sect"><b>Needs you: ${esc(BLOCKER[a.blocker] || a.blocker)}</b>Claude paused this application until you handle it, then it will carry on.</div>`;
  if (a.status === 'Dropped') h += `<div class="callout bad sect"><b>Not applied</b>${esc(a.notes || 'It did not fit your requirements.')}${failing.length ? '<br>' + failing.map(c => esc(c.k + ': ' + c.n)).join('<br>') : ''}</div>`;
  if (a.status === 'Shortlisted' && a.verdict !== 'fail') h += `<div class="callout sect"><b>Ready for you</b>This role passed the checks and has not been applied to yet.<div style="margin-top:8px"><button class="btn primary sm" type="button" data-ask="Apply to ${esc(a.company)}, ${esc(a.role)} (${esc(a.id)}), if it still passes my requirements." data-ctx="${esc(a.id)}">${ico('send')}Ask Claude to apply</button></div></div>`;
  h += `<section class="sect"><div class="sec-title">Progress</div><ol class="steps">${journey(a).map((s, i) => `<li class="${s.state}"><span class="mk">${s.state === 'done' ? ico('check') : s.state === 'skip' ? ico('x') : i + 1}</span><div><b>${esc(s.t)}</b><small>${esc(s.w)}</small></div></li>`).join('')}</ol></section>`;
  if (a.checks.length) h += `<section class="sect"><div class="sec-title">Measured against your requirements</div><div class="checks">${a.checks.map(c => `<div class="chk-row">${chk(c)}<span>${esc(c.n)}</span></div>`).join('')}</div></section>`;
  const kv = [['Where', [a.location, a.mode].filter(Boolean).join(', ')], ['Pay', a.pay], ['Track', (S.tracks.find(t => t[0] === a.track) || [0, a.track])[1]], ['Category', a.category], ['Fit', a.fit],
    ['Found', fdate(a.dateFound)], ['Applied', a.dateApplied ? fdate(a.dateApplied) : 'Not yet'], ['Next follow-up', a.fu ? fdate(a.fu.date) : ''], ['Last check', a.followUp && a.followUp.lastCheck ? fdate(a.followUp.lastCheck) : '']];
  h += `<section class="sect"><div class="sec-title">Details</div><dl class="kvs">${kv.filter(x => x[1]).map(([k, v]) => `<dt>${k}</dt><dd>${esc(v)}</dd>`).join('')}</dl></section>`;
  const rs = a.resume && !a.resumeMissing ? a.resume : '';
  h += `<section class="sect"><div class="sec-title">Resume used</div>${rs ? `<div class="row-chips" style="align-items:center;gap:10px"><span>${esc(base(rs))}</span><button class="btn sm" type="button" data-tab="resume">Preview</button><a class="btn sm" href="${fileUrl(rs)}" target="_blank" rel="noopener">${ico('ext')}Open</a></div>` : '<span class="muted">No tailored resume saved for this role yet.</span>'}</section>`;
  if ((a.learn || []).length) h += `<section class="sect"><div class="sec-title">Gaps to learn along the way</div><ul style="margin:0;padding-left:18px">${a.learn.map(x => `<li>${esc(x)}</li>`).join('')}</ul></section>`;
  if (a.notes && a.status !== 'Dropped') h += `<section class="sect"><div class="sec-title">Notes</div><p style="margin:0">${esc(a.notes)}</p></section>`;
  return h;
}
function loadFile(path){
  const e = files[path];
  if (e && e.ver === S.version) return;
  files[path] = {ver: S.version, text: e ? e.text : null};
  fetch(fileUrl(path)).then(r => r.ok ? r.text() : '(file not found)').catch(() => '(could not load)').then(t => {
    const changed = !files[path] || files[path].text !== t;
    files[path] = {ver: S.version, text: t};
    if (changed) render();
  });
}
function dTabBody(a){
  if (ui.tab === 'file' && a.files.detail){ loadFile(a.files.detail); const f = files[a.files.detail]; return f && f.text != null ? md(f.text) : '<div class="empty">Loading</div>'; }
  if (ui.tab === 'posting' && a.files.posting){ loadFile(a.files.posting); const f = files[a.files.posting]; return f && f.text != null ? md(f.text) : '<div class="empty">Loading</div>'; }
  if (ui.tab === 'resume'){
    const rs = a.resume && !a.resumeMissing ? a.resume : (a.files.resumes.find(p => p.endsWith('.pdf')) || a.files.resumes[0] || '');
    if (!rs) return '<div class="empty"><b>No resume saved</b>Nothing tailored yet.</div>';
    return rs.endsWith('.pdf') ? `<iframe src="${fileUrl(rs)}#view=FitH" title="Resume"></iframe>` : fileBox(rs);
  }
  return dSummary(a);
}
let lastDrawer = '';
function renderDrawer(id){
  const dr = $('#drawer'), a = id && appById(id);
  document.body.classList.toggle('has-drawer', !!a);
  $('#scrim').hidden = dr.hidden = !a;
  if (!a){ lastDrawer = ''; dr.innerHTML = ''; return; }
  const tabs = [['summary', 'Summary', true], ['file', 'Application file', !!a.files.detail], ['posting', 'Posting', !!a.files.posting], ['resume', 'Resume', !!(a.resume || a.files.resumes.length)]];
  if (!tabs.find(t => t[0] === ui.tab && t[2])) ui.tab = 'summary';
  const html = `<div class="d-head"><div class="d-top"><div><h2>${esc(a.company)}</h2><div class="r">${esc(a.role)}</div></div><button class="icon-btn" type="button" data-close="1" aria-label="Close">${ico('x')}</button></div>
    <div class="d-meta">${pill(a.status)}${a.bigTech ? '<span class="tag big">Big tech</span>' : ''}<span class="tag">${esc(a.id)}</span>${fuBadge(a)}${a.link ? `<a class="btn sm" href="${esc(a.link)}" target="_blank" rel="noopener noreferrer">${ico('link')}Job posting</a>` : ''}</div>
    <div class="tabs" role="tablist">${tabs.map(([k, l, on]) => `<button type="button" role="tab" data-tab="${k}" aria-selected="${ui.tab === k}"${on ? '' : ' disabled'}>${l}</button>`).join('')}</div></div>
    <div class="d-body">${dTabBody(a)}</div>`;
  if (html !== lastDrawer){
    const body = $('.d-body', dr), top = body ? body.scrollTop : 0;
    dr.innerHTML = html; lastDrawer = html;
    const nb = $('.d-body', dr); if (nb && body) nb.scrollTop = top;
  }
}

/* ---------- ask Claude: bring the Claude app forward (a prepared message is copied only when a button carries one) ---------- */
function toast(msg){
  const t = $('#toast'); t.textContent = msg; t.classList.add('show');
  clearTimeout(toast.h); toast.h = setTimeout(() => t.classList.remove('show'), 6000);
}
async function ask(text, ctxId){
  const a = (ctxId && appById(ctxId)) || (route().app && appById(route().app));
  const who = S && S.tenant.id ? `, ${S.tenant.id}` : '';
  const msg = text ? `[From the job dashboard${who}${a ? `; about ${a.id}, ${a.company}, ${a.role}` : ''}] ${text}` : '';
  try {
    const res = await fetch('/api/ask', {method: 'POST', headers: {'Content-Type': 'application/json', 'X-Dashboard-Token': TOKEN}, body: JSON.stringify({text: msg})});
    const j = await res.json();
    if (!res.ok) throw new Error(j.error || 'failed');
    if (!j.focused) toast('Open the Claude app to continue.');
    else if (msg) toast('Claude is open. Your request is copied: paste it with Cmd+V (Ctrl+V on Windows).');
  } catch (e){ toast('Could not open Claude from here. Open the Claude app yourself.'); }
}

/* ---------- render loop ---------- */
let lastMain = '', lastNav = '';
function render(){
  if (!S) return;
  const r = route();
  const view = VIEWS[r.view] ? r.view : 'overview';
  const nav = NAV.map(([k, l, ic]) => {
    const n = k === 'apps' ? S.apps.length : k === 'jobs' ? S.ledger.length : '';
    return `<a href="#/${k}" ${k === view ? 'aria-current="page"' : ''}>${ico(ic)}${l}<span class="n">${n}</span></a>`;
  }).join('');
  if (nav !== lastNav){ $('#nav').innerHTML = nav; lastNav = nav; }
  const html = VIEWS[view]();
  if (html !== lastMain){
    const ae = document.activeElement, id = ae && ae.id, pos = ae && ae.selectionStart;
    $('#main').innerHTML = html; lastMain = html;
    if (id && $('#' + id)){ const e = $('#' + id); e.focus(); try { e.setSelectionRange(pos, pos); } catch (x) {} }
  }
  renderDrawer(r.app);
  $('#brandName').textContent = S.tenant.name || 'Job search';
  document.title = (S.tenant.name ? S.tenant.name + ': ' : '') + 'Job search dashboard';
}
function setLive(on, text){
  const l = $('#live'); l.className = 'live ' + (on ? 'on' : 'off');
  $('span', l).textContent = text || (on ? 'Live' + (lastUpdate ? ', updated ' + lastUpdate : '') : 'Disconnected. Ask Claude to show the board again.');
}
async function refresh(){
  try {
    const next = await (await fetch('/api/state', {cache: 'no-store'})).json();
    const sig = (arr, key) => Object.fromEntries(arr.map(x => [x[key], JSON.stringify(x)]));
    if (S){
      const pa = sig(S.apps, 'id'), pj = sig(S.ledger, 'job_id');
      next.apps.forEach(a => { if (pa[a.id] !== JSON.stringify(a)) flashed.add('a:' + a.id); });
      next.ledger.forEach(r => { if (pj[r.job_id] !== JSON.stringify(r)) flashed.add('j:' + r.job_id); });
      if (flashed.size) setTimeout(() => flashed.clear(), 3000);
    }
    S = next;
    lastUpdate = new Date().toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'});
    setLive(true); render();
  } catch (e){ setLive(false); }
}
function connect(){
  const es = new EventSource('/events');
  es.addEventListener('hello', () => { setLive(true); if (!S) refresh(); });
  es.addEventListener('change', refresh);
  es.onerror = () => setLive(false);
}

/* ---------- events ---------- */
document.addEventListener('click', e => {
  const t = e.target;
  let n;
  if ((n = t.closest('[data-close]')) || t.id === 'scrim'){ go(route().view); return; }
  if ((n = t.closest('[data-app]'))){ e.preventDefault(); const same = route().app === n.dataset.app; if (!same) ui.tab = 'summary'; go(route().view, n.dataset.app); return; }
  if ((n = t.closest('[data-tab]'))){ if (!n.disabled){ ui.tab = n.dataset.tab; lastDrawer = ''; render(); } return; }
  if ((n = t.closest('[data-set]'))){ const [k, ...v] = n.dataset.set.split('='); ui[k] = v.join('='); ui.jLimit = 100; render(); return; }
  if ((n = t.closest('[data-more]'))){ ui.jLimit += 100; render(); return; }
  if ((n = t.closest('[data-ask]'))){ ask(n.dataset.ask, n.dataset.ctx); return; }
  if (t.closest('#theme')) cycleTheme();
});
document.addEventListener('keydown', e => {
  if (e.key === 'Escape' && route().app){ go(route().view); return; }
  if ((e.key === 'Enter' || e.key === ' ') && e.target.matches('[role="button"][data-app],tr[data-app]')){ e.preventDefault(); e.target.click(); }
});
document.addEventListener('input', e => { const k = e.target.dataset && e.target.dataset.in; if (k){ ui[k] = e.target.value; ui.jLimit = 100; render(); } });
document.addEventListener('change', e => { const k = e.target.dataset && e.target.dataset.in; if (k && e.target.tagName === 'SELECT'){ ui[k] = e.target.value; ui.jLimit = 100; render(); } });
window.addEventListener('hashchange', render);

/* ---------- theme ---------- */
const MODES = ['system', 'light', 'dark'], MODE_ICON = {system: 'auto', light: 'sun', dark: 'moon'};
let mode = 'system';
try { const s = localStorage.getItem('jd-theme'); if (MODES.includes(s)) mode = s; } catch (e) {}
function applyTheme(){
  if (mode === 'system') document.documentElement.removeAttribute('data-theme'); else document.documentElement.setAttribute('data-theme', mode);
  $('#theme').innerHTML = ico(MODE_ICON[mode]); $('#theme').title = 'Theme: ' + mode;
  try { localStorage.setItem('jd-theme', mode); } catch (e) {}
}
function cycleTheme(){ mode = MODES[(MODES.indexOf(mode) + 1) % 3]; applyTheme(); }
applyTheme();
setLive(false, 'Connecting');
$('#live').className = 'live';
connect();
})();
