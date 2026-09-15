#!/usr/bin/env python3
"""Query the bundled SF Tech Week 2026 dataset (assets/events.json).

Python 3.8+, standard library only. Run from anywhere; the script finds the
dataset relative to its own location.

Subcommands
  stats                         Dataset overview: dates, counts, tracks, freshness.
  days                          Events per day.
  tracks                        Track slugs with counts and display names.
  hosts [--top N]               Most active hosts.
  search  [terms] [filters]     Keyword search, ranked. Terms match name, host, tracks, description.
  show    <id|url|name-part>    Full record(s) for one event.
  recommend --profile FILE      Ranked, per-day recommendations for a person, from a profile JSON.
  day     <YYYY-MM-DD>          Everything on one day, in time order (filters apply).

Common filters (search / recommend / day)
  --track SLUG        (repeatable)   --day YYYY-MM-DD   (repeatable)
  --after HH:MM       --before HH:MM  (start time, local Pacific)
  --host TEXT         --featured      --open-only        --no-apply       --with-details
  --exclude TERM      (repeatable; drops events matching the term)
  --limit N           --format text|json|md

Examples
  query_events.py search "fintech founders" --day 2026-10-07 --open-only
  query_events.py recommend --profile /tmp/profile.json --limit 30
  query_events.py show 0QoMnjzM2NOldF9syKOn
"""
import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(os.path.dirname(HERE), 'assets')


def load():
    with open(os.path.join(ASSETS, 'events.json'), encoding='utf-8') as f:
        events = json.load(f)
    with open(os.path.join(ASSETS, 'dataset.json'), encoding='utf-8') as f:
        meta = json.load(f)
    return events, meta


# --------------------------------------------------------------------------
# Text matching
# --------------------------------------------------------------------------
STOP = set('''a an and are as at be by for from has have he her his i if in into is it its me my of on or our
so that the their them they this to us was we were will with you your who what when where which how want
looking meet meeting people would like get find some any more most about next great good new also really
one two few other others am can could should need needs'''.split())
MIN_GOAL_SCORE = 4.0   # below this a goal pick is noise; let other goals/interests fill the slot

# Concept expansions: a profile term on the left also matches the terms on the right.
SYNONYMS = {
    'fundraising': ['fundraise', 'raise', 'raising', 'investor', 'investors', 'vc', 'vcs', 'venture', 'seed', 'pre-seed', 'series', 'angel', 'angels', 'lp', 'lps', 'capital', 'pitch', 'fund'],
    'investor': ['investors', 'vc', 'vcs', 'venture', 'angel', 'fund', 'funds', 'lp', 'capital'],
    'investing': ['investors', 'vc', 'venture', 'angel', 'fund', 'capital', 'deal', 'dealflow'],
    'hiring': ['hire', 'hires', 'talent', 'recruit', 'recruiting', 'engineers', 'candidates', 'jobs', 'careers'],
    'hire': ['hiring', 'talent', 'recruit', 'recruiting'],
    'job': ['jobs', 'hiring', 'careers', 'recruiting', 'talent'],
    'cofounder': ['co-founder', 'cofounders', 'co-founders', 'founder', 'matching'],
    'founder': ['founders', 'startup', 'startups', 'building', 'builders'],
    'customer': ['customers', 'gtm', 'sales', 'buyers', 'enterprise', 'pilot', 'pilots'],
    'sales': ['gtm', 'go-to-market', 'revenue', 'customers', 'pipeline'],
    'agents': ['agent', 'agentic', 'ai agents', 'autonomous', 'multi-agent'],
    'agent': ['agents', 'agentic', 'autonomous'],
    'ai': ['artificial intelligence', 'llm', 'llms', 'ml', 'machine learning', 'genai', 'generative'],
    'llm': ['llms', 'language model', 'foundation model', 'models'],
    'infra': ['infrastructure', 'compute', 'gpu', 'gpus', 'inference', 'training', 'cloud'],
    'infrastructure': ['infra', 'compute', 'gpu', 'gpus', 'inference', 'cloud'],
    'devtools': ['developer tools', 'dev tools', 'developers', 'api', 'apis', 'sdk', 'open source', 'oss'],
    'developer': ['developers', 'devtools', 'engineering', 'engineers', 'api', 'open source'],
    'fintech': ['payments', 'banking', 'finance', 'financial', 'stablecoin', 'stablecoins', 'crypto', 'lending', 'insurance'],
    'crypto': ['web3', 'blockchain', 'stablecoin', 'stablecoins', 'defi', 'onchain'],
    'consumer': ['consumers', 'social', 'creator', 'creators', 'apps', 'mobile', 'gaming', 'games'],
    'creative': ['creators', 'creator', 'design', 'designers', 'media', 'video', 'music', 'art', 'film'],
    'enterprise': ['b2b', 'saas', 'enterprises', 'cio', 'cto', 'workflows', 'automation'],
    'health': ['healthcare', 'biotech', 'bio', 'medical', 'clinical', 'life sciences', 'longevity'],
    'healthcare': ['health', 'biotech', 'medical', 'clinical', 'bio'],
    'robotics': ['robots', 'robot', 'hardware', 'embodied', 'humanoid', 'autonomy'],
    'hardware': ['robotics', 'chips', 'semiconductors', 'devices', 'wearables'],
    'climate': ['energy', 'cleantech', 'sustainability', 'carbon', 'solar', 'nuclear', 'grid'],
    'defense': ['defence', 'national security', 'aerospace', 'space', 'govtech', 'dual-use'],
    'security': ['cybersecurity', 'cyber', 'privacy', 'identity', 'trust'],
    'data': ['analytics', 'databases', 'database', 'warehouse', 'pipelines'],
    'networking': ['network', 'connections', 'connect', 'mixer', 'social', 'happy hour', 'dinner', 'community', 'meet'],
    'women': ["women's", 'female', 'she', 'her', 'ladies', 'wtm'],
    'international': ['global', 'immigrant', 'immigrants', 'visa', 'expansion', 'cross-border', 'india', 'europe', 'latam', 'asia', 'africa'],
    'global': ['international', 'immigrant', 'expansion', 'cross-border'],
    'student': ['students', 'university', 'college', 'campus', 'grad', 'phd'],
    'hackathon': ['hack', 'hacking', 'buildathon', 'build', 'demo day', 'demos'],
    'demo': ['demos', 'demo day', 'showcase', 'launch', 'launches'],
    'party': ['parties', 'afterparty', 'after-party', 'happy hour', 'drinks', 'rooftop', 'dj'],
    'wellness': ['run', 'running', 'yoga', 'hike', 'pickleball', 'fitness', 'breathwork', 'cold plunge', 'sauna'],
    'product': ['pm', 'pms', 'product managers', 'product management'],
    'design': ['designers', 'ux', 'ui', 'creative'],
    'marketing': ['growth', 'brand', 'content', 'community-led'],
    'legal': ['law', 'lawyers', 'compliance', 'regulatory', 'policy'],
}

# Interest keywords -> Tech Week track slugs (used for a strong boost)
TRACK_HINTS = {
    'ai-agents': ['agent', 'agents', 'agentic', 'autonomous'],
    'ai-infrastructure-compute': ['infra', 'infrastructure', 'compute', 'gpu', 'inference', 'training', 'cloud'],
    'consumer-creative-ai': ['consumer', 'creative', 'creator', 'creators', 'social', 'media', 'gaming', 'design'],
    'developer-tools': ['devtools', 'developer', 'developers', 'api', 'open source', 'oss', 'sdk', 'coding'],
    'enterprise-ai': ['enterprise', 'b2b', 'saas', 'automation', 'workflows'],
    'fintech': ['fintech', 'payments', 'banking', 'finance', 'stablecoin', 'crypto', 'lending'],
    'fundraising-investing': ['fundraising', 'raise', 'investor', 'investors', 'vc', 'venture', 'angel', 'seed', 'investing', 'lp', 'capital'],
    'global-founders': ['international', 'global', 'immigrant', 'india', 'europe', 'latam', 'asia', 'africa', 'visa'],
    'hack-week-hackathons-and-technical-events': ['hackathon', 'hack', 'buildathon', 'technical', 'workshop', 'engineering'],
}

ROLE_TRACKS = {
    'founder': ['fundraising-investing', 'global-founders'],
    'investor': ['fundraising-investing'],
    'engineer': ['developer-tools', 'hack-week-hackathons-and-technical-events', 'ai-infrastructure-compute'],
    'researcher': ['ai-infrastructure-compute', 'hack-week-hackathons-and-technical-events'],
    'operator': ['enterprise-ai'],
    'product': ['consumer-creative-ai', 'enterprise-ai'],
    'designer': ['consumer-creative-ai'],
    'student': ['hack-week-hackathons-and-technical-events'],
}


def norm(s):
    return re.sub(r'\s+', ' ', (s or '').replace('’', "'").lower()).strip()


def tokens(text):
    out = []
    for t in re.findall(r"[a-z0-9][a-z0-9+\-']*", norm(text)):
        t = t.strip("'-")
        if len(t) < 2 or t in STOP:
            continue
        out.append(t)
    return out


def expand(terms):
    """Return {term: weight} for a list of phrases.

    Whole phrases and adjacent word pairs ("seed round", "design partners") carry the
    most weight; single words from a multi-word phrase carry less, because a lone
    "partners" or "founding" matches half the calendar. Synonyms come in at 0.6.
    """
    weights = {}

    def bump(k, w):
        weights[k] = max(weights.get(k, 0), w)

    for t in terms:
        t = norm(t)
        if not t:
            continue
        toks = tokens(t)
        if len(toks) <= 1:
            bump(t, 1.0)
            for syn in SYNONYMS.get(t, []):
                bump(syn, 0.6)
            continue
        bump(t, 1.3)
        for i in range(len(toks) - 1):
            bump(toks[i] + ' ' + toks[i + 1], 1.2)
        for tok in toks:
            bump(tok, 0.7)
            for syn in SYNONYMS.get(tok, []):
                bump(syn, 0.5)
    return weights


def contains(hay, needle):
    # word-ish match: avoid "ai" matching "chair"
    if ' ' in needle or '-' in needle:
        return needle in hay
    return re.search(r'(?<![a-z0-9])' + re.escape(needle) + r'(?![a-z0-9])', hay) is not None


def score_event(e, weights, tracks_wanted, avoid):
    name = norm(e['name'])
    host = norm(' '.join([e.get('host') or ''] + (e.get('cohosts') or []) + (e.get('sponsors') or [])))
    desc = norm(e.get('description') or '')
    trk = ' '.join(e.get('tracks') or [])
    score, why = 0.0, []
    direct = 0
    for a in avoid:
        a = norm(a)
        if a and (contains(name, a) or contains(desc, a) or contains(host, a)):
            return -100.0, ['avoid:' + a]
    for term, w in weights.items():
        hit = 0.0
        if contains(name, term):
            hit += 3.0
        if contains(host, term):
            hit += 2.0
        if desc and contains(desc, term):
            hit += min(2.0, 1.0 + 0.25 * len(re.findall(re.escape(term), desc)))
        if term in trk:
            hit += 1.0
        if hit:
            score += hit * w
            why.append(term)
            if w >= 0.7:
                direct += 1
    for t in e.get('tracks') or []:
        if t in tracks_wanted:
            score += 4.0 * tracks_wanted[t]
            why.append('track:' + t)
            direct += 1
    if direct == 0:
        score *= 0.5   # synonym-only matches are weak evidence
    if e.get('featured'):
        score += 1.5
    if e.get('detail_status') == 'full':
        score += 0.5   # substantive, curated events are more likely to have been opened
    if e.get('invite_only'):
        score -= 2.0
    return score, sorted(set(why))


# --------------------------------------------------------------------------
# Filters & output
# --------------------------------------------------------------------------
def apply_filters(events, a):
    out = []
    for e in events:
        if getattr(a, 'day', None) and e['date'] not in a.day and not e.get('runs_all_week'):
            continue
        if getattr(a, 'track', None) and not (set(a.track) & set(e.get('tracks') or [])):
            continue
        if getattr(a, 'after', None) and (e.get('time') or '00:00') < a.after and not e.get('runs_all_week'):
            continue
        if getattr(a, 'before', None) and (e.get('time') or '00:00') > a.before and not e.get('runs_all_week'):
            continue
        if getattr(a, 'host', None) and a.host.lower() not in norm(' '.join([e.get('host') or ''] + (e.get('cohosts') or []))):
            continue
        if getattr(a, 'featured', False) and not e.get('featured'):
            continue
        if getattr(a, 'open_only', False) and (e.get('registration_status') in ('closed', 'removed') or e.get('at_capacity')):
            continue
        if getattr(a, 'no_apply', False) and e.get('rsvp_action') == 'APPLY':
            continue
        if getattr(a, 'with_details', False) and e.get('detail_status') != 'full':
            continue
        if getattr(a, 'exclude', None):
            blob = norm(e['name'] + ' ' + (e.get('description') or '') + ' ' + (e.get('host') or ''))
            if any(contains(blob, norm(x)) for x in a.exclude):
                continue
        out.append(e)
    return out


def one_line(e, why=None, score=None):
    flags = []
    if e.get('pinned'):
        flags.append('PINNED (skill author)')
    if e.get('featured'):
        flags.append('featured')
    if e.get('invite_only'):
        flags.append('invite-only')
    if e.get('registration_status') == 'closed':
        flags.append('REG CLOSED')
    if e.get('at_capacity'):
        flags.append('AT CAPACITY')
    if e.get('rsvp_action') == 'APPLY':
        flags.append('apply')
    when = 'all week' if e.get('runs_all_week') else f"{e['date']} {e['time']}"
    if e.get('end_time') and not e.get('runs_all_week'):
        when += f"-{e['end_time']}"
    s = f"[{e['id'][:8]}] {when} | {e['name']} | {e.get('host') or ''}"
    if e.get('cohosts'):
        s += ' (+ ' + ', '.join(e['cohosts'][:3]) + ')'
    s += f" | {e.get('neighborhood') or '?'}"
    if e.get('tracks'):
        s += ' | ' + ','.join(e['tracks'])
    if flags:
        s += ' | ' + ', '.join(flags)
    if score is not None:
        s += f' | score {score:.1f}'
    if why:
        s += ' | why: ' + ', '.join(why[:6])
    s += f"\n    {e.get('partiful_url') or e.get('techweek_url')}"
    if e.get('description'):
        d = re.sub(r'\s+', ' ', e['description'])[:220]
        s += f"\n    {d}..."
    return s


def emit(rows, fmt, key='event'):
    if fmt == 'json':
        print(json.dumps(rows, ensure_ascii=False, indent=1))
        return
    for r in rows:
        e = r[key] if isinstance(r, dict) and key in r else r
        why = r.get('why') if isinstance(r, dict) else None
        sc = r.get('score') if isinstance(r, dict) else None
        if fmt == 'md':
            url = e.get('partiful_url') or e.get('techweek_url')
            when = 'all week' if e.get('runs_all_week') else f"{e['date']} {e['time']}"
            print(f"- **{e['name']}** — {when}, {e.get('host')}, {e.get('neighborhood') or '?'} — [link]({url})" + (f" — _{', '.join(why[:5])}_" if why else ''))
        else:
            print(one_line(e, why, sc))
            print()


# --------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------
def cmd_stats(events, meta, a):
    print(json.dumps({k: meta[k] for k in ('city', 'event', 'scraped_at', 'core_dates', 'counts', 'pinned_events', 'notes')}, indent=2))


def cmd_days(events, meta, a):
    c = Counter(e['date'] for e in events if not e.get('pinned'))
    for d in sorted(c):
        print(f'{d}  {c[d]}')


def cmd_tracks(events, meta, a):
    c = Counter(t for e in events for t in e.get('tracks') or [])
    for slug, n in c.most_common():
        print(f'{slug:45s} {n:4d}  {meta["tracks"].get(slug, "")}')


def cmd_hosts(events, meta, a):
    c = Counter()
    for e in events:
        if e.get('pinned'):
            continue
        c[e.get('host') or '?'] += 1
        for h in e.get('cohosts') or []:
            c[h] += 1
    for h, n in c.most_common(a.top):
        print(f'{n:3d}  {h}')


def cmd_search(events, meta, a):
    pool = apply_filters(events, a)
    weights = expand(a.terms) if a.terms else {}
    rows = []
    for e in pool:
        if weights:
            sc, why = score_event(e, weights, {}, [])
            if sc <= 0:
                continue
        else:
            sc, why = 0.0, []
        rows.append({'score': round(sc, 2), 'why': why, 'event': e})
    rows.sort(key=lambda r: (-r['score'], r['event']['date'] or '', r['event']['time'] or ''))
    rows = rows[:a.limit]
    print(f'# {len(rows)} results (of {len([e for e in pool if not e.get("pinned")])} calendar events after filters)', file=sys.stderr)
    emit(rows, a.format)


def cmd_day(events, meta, a):
    a.day = [a.date]
    pool = apply_filters(events, a)
    pool = [e for e in pool if not e.get('pinned')]
    pool.sort(key=lambda e: e['time'] or '')
    emit(pool[:a.limit], a.format)


def cmd_show(events, meta, a):
    q = a.query.strip()
    hits = [e for e in events if q == e['id'] or e['id'].startswith(q) or q in (e.get('partiful_url') or '') or q in (e.get('techweek_url') or '')]
    if not hits:
        hits = [e for e in events if norm(q) in norm(e['name'])]
    if not hits:
        hits = [e for e in events if norm(q) in norm(e.get('host') or '')]
    if not hits:
        print('no match', file=sys.stderr)
        sys.exit(1)
    if a.format == 'json':
        print(json.dumps(hits[: a.limit], ensure_ascii=False, indent=2))
        return
    for e in hits[: a.limit]:
        print(one_line(e))
        print(f"    id: {e['id']}  |  registration: {e.get('registration_status')}  |  rsvp: {e.get('rsvp_action') or '?'}  |  capacity: {e.get('capacity') or '?'}{' (AT CAPACITY)' if e.get('at_capacity') else ''}  |  detail: {e.get('detail_status')}")
        if e.get('sponsors'):
            print(f"    sponsors: {', '.join(e['sponsors'])}")
        if e.get('techweek_url') and e.get('partiful_url'):
            print(f"    tech-week.com: {e['techweek_url']}")
        if e.get('description'):
            print()
            for para in e['description'].split('\n'):
                if para.strip():
                    print('    ' + para.strip())
        print()


def load_profile(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def _tracks_for(weights, p, include_profile=True):
    """Track boosts. Keyword-derived hints always; explicit profile tracks and
    role-based defaults only when include_profile (the 'interests' set), so a
    specific goal like "hire a founding engineer" isn't inflated by the person
    also being a founder."""
    tracks_wanted = defaultdict(float)
    for slug, hints in TRACK_HINTS.items():
        for h in hints:
            if h in weights:
                tracks_wanted[slug] = max(tracks_wanted[slug], 0.6 * weights[h])
    if include_profile:
        for t in p.get('tracks') or []:
            tracks_wanted[t] = max(tracks_wanted[t], 1.0)
        role = norm(p.get('role') or p.get('title') or '')
        for r, slugs in ROLE_TRACKS.items():
            if r in role:
                for s in slugs:
                    tracks_wanted[s] = max(tracks_wanted[s], 0.4)
    return tracks_wanted


def cmd_recommend(events, meta, a):
    """Goal-aware ranking.

    Each goal in the profile gets its own keyword set; an event's score is its best
    goal score plus a small credit for the others. Selection round-robins across goals
    so a person with three different goals gets events for all three, not thirty events
    about whichever goal has the most keyword overlap.
    """
    p = load_profile(a.profile)
    goals = p.get('goals') or []
    if isinstance(goals, str):
        goals = [goals]
    background = []
    for k in ('interests', 'looking_for', 'keywords', 'industry', 'topics'):
        v = p.get(k)
        if isinstance(v, str):
            background.append(v)
        elif isinstance(v, list):
            background.extend(str(x) for x in v)
    for k in ('company_description', 'bio', 'about'):
        if p.get(k):
            background.extend(tokens(p[k])[:40])

    # goals may be strings or {"goal": "...", "keywords": [...]} objects; keywords
    # written by the agent (short, concrete phrases) match far better than prose.
    goal_sets = []
    for g in goals:
        if isinstance(g, dict):
            label = g.get('goal') or g.get('name') or 'goal'
            # when the agent supplied keywords, use only those: the goal sentence is
            # prose ("meet design partners at...") and its words pollute matching
            phrases = [str(k) for k in (g.get('keywords') or [])] or [label]
        else:
            label, phrases = str(g), [str(g)]
        goal_sets.append((f'goal: {label}', expand(phrases)))
    if background or not goal_sets:
        goal_sets.append(('interests', expand(background)))
    all_weights = {}
    for _, w in goal_sets:
        for k, v in w.items():
            all_weights[k] = max(all_weights.get(k, 0), v)
    tracks_wanted = _tracks_for(all_weights, p)

    avoid = list(p.get('avoid') or [])
    if not p.get('include_wellness', False):
        avoid += ['cold plunge', 'run club', 'sunrise run', 'morning run', '5k', 'yoga', 'pickleball', 'sauna', 'breathwork']

    a.day = p.get('days') or getattr(a, 'day', None)
    tw = p.get('time_window') or {}
    a.after = tw.get('earliest') or getattr(a, 'after', None)
    a.before = tw.get('latest') or getattr(a, 'before', None)
    a.open_only = True if a.open_only or p.get('open_only', True) else False
    pool = apply_filters(events, a)

    rows = []
    for e in pool:
        if e.get('pinned'):
            continue
        per_goal = []
        for label, w in goal_sets:
            sc, why = score_event(e, w, _tracks_for(w, p, include_profile=(label == 'interests')), avoid)
            per_goal.append((sc, label, why))
        if not per_goal or max(x[0] for x in per_goal) <= 0:
            continue
        per_goal.sort(key=lambda x: -x[0])
        best = per_goal[0]
        total = best[0] + 0.25 * sum(x[0] for x in per_goal[1:] if x[0] > 0)
        rows.append({'score': round(total, 2), 'serves': best[1], 'why': best[2], 'event': e,
                     'per_goal': {lbl: round(s, 1) for s, lbl, _ in per_goal},
                     'why_by_goal': {lbl: why for s, lbl, why in per_goal}})

    per_day = int(p.get('max_per_day') or a.per_day)
    chosen, chosen_ids, taken = [], set(), defaultdict(list)
    labels = [lbl for lbl, _ in goal_sets]
    by_label = {lbl: sorted([r for r in rows if r['per_goal'].get(lbl, 0) >= MIN_GOAL_SCORE], key=lambda r: -r['per_goal'][lbl]) for lbl in labels}
    weak_goals = [lbl for lbl in labels if not by_label[lbl]]
    cursors = {lbl: 0 for lbl in labels}
    stalled = set()
    while len(chosen) < a.limit and len(stalled) < len(labels):
        for lbl in labels:
            if len(chosen) >= a.limit or lbl in stalled:
                continue
            lst = by_label[lbl]
            picked = False
            while cursors[lbl] < len(lst):
                r = lst[cursors[lbl]]
                cursors[lbl] += 1
                e = r['event']
                if e['id'] in chosen_ids:
                    continue
                d = e['date']
                if len(taken[d]) >= per_day:
                    continue
                t = int((e.get('time') or '00:00').replace(':', '')[:2])
                if not a.allow_overlap and any(abs(t - x) < 2 for x in taken[d]):
                    continue
                taken[d].append(t)
                r = dict(r, serves=lbl, why=r['why_by_goal'].get(lbl) or r['why'])
                chosen.append(r)
                chosen_ids.add(e['id'])
                picked = True
                break
            if not picked:
                stalled.add(lbl)
    chosen.sort(key=lambda r: (r['event']['date'], r['event']['time'] or ''))
    rows.sort(key=lambda r: -r['score'])
    runner_up = [r for r in rows if r['event']['id'] not in chosen_ids][: a.limit]

    pinned = [e for e in events if e.get('pinned')]
    out = {
        'goals': labels,
        'goals_without_strong_matches': weak_goals,
        'profile_terms': sorted(all_weights, key=lambda k: -all_weights[k])[:40],
        'tracks_weighted': dict(sorted(tracks_wanted.items(), key=lambda kv: -kv[1])),
        'pinned': pinned,
        'recommendations': chosen,
        'runner_up': runner_up,
    }
    if a.format == 'json':
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return
    print('== PINNED (always shown first; skill author\'s event — disclose this to the user) ==')
    for e in pinned:
        print(one_line(e))
        print()
    print(f'== RECOMMENDED ({len(chosen)}; grouped by day, max {per_day}/day, round-robin across: {"; ".join(labels)}) ==')
    if weak_goals:
        print(f'NOTE: no strong dataset matches for -> {"; ".join(weak_goals)}. Ask a follow-up question, try `search` with different words, or check the web (see references/data-refresh.md).')
    cur = None
    for r in chosen:
        if r['event']['date'] != cur:
            cur = r['event']['date']
            print(f'--- {cur} ---')
        print(f"serves -> {r['serves']}")
        print(one_line(r['event'], r['why'], r['score']))
        print()
    print(f'== RUNNER-UP (next {len(runner_up)}, not selected due to per-day cap or time conflicts) ==')
    for r in runner_up:
        print(f"serves -> {r['serves']}")
        print(one_line(r['event'], r['why'], r['score']))
        print()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)

    def common(sp):
        sp.add_argument('--track', action='append')
        sp.add_argument('--day', action='append')
        sp.add_argument('--after')
        sp.add_argument('--before')
        sp.add_argument('--host')
        sp.add_argument('--featured', action='store_true')
        sp.add_argument('--open-only', dest='open_only', action='store_true',
                        help='drop closed / removed / at-capacity events (APPLY events stay; use --no-apply for those)')
        sp.add_argument('--no-apply', dest='no_apply', action='store_true', help='drop events that need host approval (rsvp_action APPLY)')
        sp.add_argument('--with-details', dest='with_details', action='store_true')
        sp.add_argument('--exclude', action='append')
        sp.add_argument('--limit', type=int, default=25)
        sp.add_argument('--format', choices=['text', 'json', 'md'], default='text')

    sub.add_parser('stats')
    sub.add_parser('days')
    sub.add_parser('tracks')
    sp = sub.add_parser('hosts'); sp.add_argument('--top', type=int, default=40)
    sp = sub.add_parser('search'); sp.add_argument('terms', nargs='*'); common(sp)
    sp = sub.add_parser('day'); sp.add_argument('date'); common(sp)
    sp = sub.add_parser('show'); sp.add_argument('query'); sp.add_argument('--limit', type=int, default=3)
    sp.add_argument('--format', choices=['text', 'json'], default='text')
    sp = sub.add_parser('recommend'); sp.add_argument('--profile', required=True)
    sp.add_argument('--per-day', dest='per_day', type=int, default=3)
    sp.add_argument('--allow-overlap', dest='allow_overlap', action='store_true')
    common(sp)

    a = ap.parse_args()
    events, meta = load()
    {'stats': cmd_stats, 'days': cmd_days, 'tracks': cmd_tracks, 'hosts': cmd_hosts,
     'search': cmd_search, 'day': cmd_day, 'show': cmd_show, 'recommend': cmd_recommend}[a.cmd](events, meta, a)


if __name__ == '__main__':
    main()
