#!/usr/bin/env python3
"""Merge a fresh calendar pull (output of scripts/refresh_calendar.js) into
assets/<city>/events.json, keeping the Partiful details already collected.

Usage:
  merge_refresh.py fresh.json                    # report what changed (city=sf), write nothing
  merge_refresh.py fresh.json --city la --write   # update assets/la/events.json + dataset.json

For a city with no bundled dataset yet, use bootstrap_city.py instead — this
script is for refreshing a city that's already been onboarded.

Records already in the dataset keep their description/capacity/partiful_url
(those come from Partiful and don't change often); calendar-level fields
(name, host, date, time, neighborhood, tracks, registration_status, featured)
are refreshed. The fresh file may be either the full {city, fetchedAt, events}
object from refresh_calendar.js or a bare JSON array of events (if you pulled
the events out of the browser in slices, concatenate them into one array).
New events are added with detail_status "none". Events that disappeared from the calendar are kept but marked registration_status
"removed" so earlier recommendations still resolve.
"""
import argparse
import json
import os
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(os.path.dirname(HERE), 'assets')
CAL_FIELDS = ['name', 'host', 'cohosts', 'sponsors', 'date', 'time', 'neighborhood', 'tracks',
              'featured', 'invite_only', 'registration_status', 'techweek_url']


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('fresh_path')
    ap.add_argument('--city', default='sf', help='city slug already bundled under assets/ (default sf)')
    ap.add_argument('--write', action='store_true')
    args = ap.parse_args()
    fresh_path, write = args.fresh_path, args.write
    city_dir = os.path.join(ASSETS, args.city)
    with open(fresh_path, encoding='utf-8') as f:
        fresh = json.load(f)
    if isinstance(fresh, str):          # tool returned a JSON string literal
        fresh = json.loads(fresh)
    if isinstance(fresh, list):
        fresh = {'events': fresh}
    fresh_events = {e['id']: e for e in fresh['events']}

    with open(os.path.join(city_dir, 'events.json'), encoding='utf-8') as f:
        events = json.load(f)
    with open(os.path.join(city_dir, 'dataset.json'), encoding='utf-8') as f:
        meta = json.load(f)

    by_id = {e['id']: e for e in events}
    added, changed, removed = [], [], []
    for eid, fe in fresh_events.items():
        if eid in by_id:
            cur = by_id[eid]
            diffs = {k: (cur.get(k), fe.get(k)) for k in CAL_FIELDS if cur.get(k) != fe.get(k) and fe.get(k) is not None}
            if cur.get('detail_status') == 'full':
                # Partiful's title/neighborhood are the richer source; keep them.
                diffs.pop('name', None)
                diffs.pop('neighborhood', None)
            for k in diffs:
                cur[k] = fe[k]
            # tech-week.com re-signs its /go/event/ links on every fetch; old ones keep
            # working, so a URL-only change is not worth reporting.
            diffs.pop('techweek_url', None)
            if diffs:
                changed.append((cur['name'], diffs))
        else:
            rec = {k: fe.get(k) for k in CAL_FIELDS}
            rec.update({'id': eid, 'end_time': None, 'start_utc': None, 'end_utc': None,
                        'approx_location': '', 'rsvp_action': None, 'capacity': None,
                        'at_capacity': None, 'partiful_url': None, 'description': '',
                        'detail_status': 'none', 'source': 'tech-week.com calendar'})
            events.append(rec)
            added.append(rec['name'])
    for e in events:
        if e.get('pinned') or e['id'] in fresh_events:
            continue
        if e.get('registration_status') != 'removed':
            e['registration_status'] = 'removed'
            removed.append(e['name'])

    print(f'fresh: {len(fresh_events)}  existing: {len(by_id)}  added: {len(added)}  changed: {len(changed)}  removed: {len(removed)}')
    for n in added[:20]:
        print('  + ', n)
    for n, d in changed[:20]:
        print('  ~ ', n, {k: v[1] for k, v in d.items()})
    for n in removed[:20]:
        print('  - ', n)

    if write:
        events.sort(key=lambda r: (0 if r.get('pinned') else 1, r.get('date') or '', r.get('time') or ''))
        with open(os.path.join(city_dir, 'events.json'), 'w', encoding='utf-8') as f:
            json.dump(events, f, ensure_ascii=False, indent=0)
        meta['scraped_at'] = fresh.get('fetchedAt', str(date.today()))[:10]
        meta['counts']['events'] = len([e for e in events if not e.get('pinned')])
        with open(os.path.join(city_dir, 'dataset.json'), 'w', encoding='utf-8') as f:
            json.dump(meta, f, indent=2)
        print('written.')
        import subprocess
        subprocess.run([sys.executable, os.path.join(HERE, 'build_index.py'), '--city', args.city], check=False)


if __name__ == '__main__':
    main()
