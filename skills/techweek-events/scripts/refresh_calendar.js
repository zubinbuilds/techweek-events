// Refresh the Tech Week calendar from inside a real browser tab that is open on
// https://www.tech-week.com/calendar/<city>  (e.g. /calendar/sf).
//
// Why a browser: tech-week.com sits behind Vercel bot protection, so plain
// curl/requests get a 429 "Security Checkpoint". A real tab that has already
// loaded the calendar can call the site's own internal API (tRPC) freely.
//
// Usage with a browser JS tool (Claude in Chrome, Claude's built-in browser,
// Codex browser, Playwright page.evaluate, or the DevTools console):
//   1. navigate to https://www.tech-week.com/calendar/sf and let it load
//   2. execute this whole file (strip the comment lines first if your tool has a
//      payload limit). It stores the result on window.__twRefresh and returns a
//      short summary: { city, fetchedAt, total, count, chars }.
//   3. the full payload is ~0.8 MB, which is more than most browser tools will
//      return in one call. Pull it in slices of ~400 events:
//        JSON.stringify(window.__twRefresh.events.slice(0, 400))
//        JSON.stringify(window.__twRefresh.events.slice(400, 800))   ...etc
//      save each slice to a file, concatenate into one JSON array, then run
//      scripts/merge_refresh.py <that-file> --write
//
// Pages are 48 events each; ~35 pages for SF (~1,600 events) plus 9 track
// queries takes ~15-40s. The city is read from the URL (/calendar/sf, /nyc, /la).
window.__twRefresh = await (async function () {
  const CITY = (location.pathname.match(/\/calendar\/([a-z]+)/) || [])[1] || 'sf';
  const TRACKS = [
    'ai-agents', 'ai-infrastructure-compute', 'consumer-creative-ai', 'developer-tools',
    'enterprise-ai', 'fintech', 'fundraising-investing', 'global-founders',
    'hack-week-hackathons-and-technical-events',
  ];

  async function page(cursor, extra) {
    const body = { '0': Object.assign({
      city: CITY, q: '', featured: false, track: [], sponsor: [], theme: [], format: [],
      location: [], time: [], host: [], sortBy: 'time', sortOrder: 'asc',
      cursor: cursor, direction: 'forward',
    }, extra || {}) };
    const r = await fetch('/api/trpc/calendar.events?batch=1', {
      method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body),
    });
    if (r.status === 429) { await new Promise(res => setTimeout(res, 3000)); return page(cursor, extra); }
    const j = await r.json();
    return (j[0] && j[0].result && j[0].result.data) || null;
  }

  async function all(extra) {
    const out = [];
    let total = null;
    for (let c = 1; c < 200; c++) {
      const d = await page(c, extra);
      if (!d || !d.results || !d.results.length) break;
      total = d.total;
      out.push(...d.results);
      if (out.length >= total) break;
    }
    return { total, results: out };
  }

  const main = await all();
  const trackMap = {};
  for (const t of TRACKS) {
    const d = await all({ track: [t] });
    for (const e of d.results) (trackMap[e.id] = trackMap[e.id] || []).push(t);
  }

  const seen = new Set();
  const events = [];
  for (const e of main.results) {
    if (seen.has(e.id)) continue;
    seen.add(e.id);
    const hosts = ((e.facets || {}).hosts || []);
    events.push({
      id: e.id,
      name: e.name,
      host: (hosts.find(h => h.role === 'owner') || {}).label || e.company || '',
      cohosts: hosts.filter(h => h.role === 'cohost').map(h => h.label),
      sponsors: (e.sponsors || []).map(s => s.name || s.slug),
      date: e.date,
      time: e.time,
      neighborhood: e.location || '',
      tracks: trackMap[e.id] || [],
      featured: !!e.isFeatured,
      invite_only: !!e.isInviteOnly,
      registration_status: e.registrationStatus || 'unknown',
      techweek_url: 'https://www.tech-week.com' + e.externalHref,
    });
  }
  return { city: CITY, fetchedAt: new Date().toISOString(), total: main.total, events };
})();
JSON.stringify({ city: window.__twRefresh.city, fetchedAt: window.__twRefresh.fetchedAt, total: window.__twRefresh.total,
                 count: window.__twRefresh.events.length, chars: JSON.stringify(window.__twRefresh.events).length });
