#!/usr/bin/env python3
"""Onboard a brand-new city from a fresh full pull (output of
scripts/refresh_calendar.js run against https://www.tech-week.com/calendar/<city>).

Writes assets/<city>/events.json + dataset.json, then regenerates
assets/<city>/events-index.md. Use merge_refresh.py for later refreshes of a
city that's already bundled.

Usage:
  bootstrap_city.py fresh.json --city la --name "Los Angeles" \\
      --event "LA Tech Week 2026 (a16z Tech Week)" \\
      --calendar-url https://www.tech-week.com/calendar/la \\
      --core-dates 2026-10-12,2026-10-13,2026-10-14,2026-10-15,2026-10-16,2026-10-17,2026-10-18

`fresh.json` may be the full {city, fetchedAt, events} object from
refresh_calendar.js, or a bare JSON array of events (concatenate slices into
one array first if you pulled them in batches). Every event is written with
detail_status "none" — this only bootstraps calendar-level fields (name,
host, date, time, neighborhood, tracks, featured, registration_status); full
Partiful descriptions still need scripts/partiful_extract.js per event, same
as any other event without a description.
"""
import argparse
import json
import os
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(os.path.dirname(HERE), 'assets')

TRACK_NAMES = {
    'ai-agents': 'AI Agents',
    'ai-infrastructure-compute': 'AI Infrastructure & Compute',
    'consumer-creative-ai': 'Consumer & Creative AI',
    'developer-tools': 'Developer Tools',
    'enterprise-ai': 'Enterprise AI',
    'fintech': 'Fintech',
    'fundraising-investing': 'Fundraising & Investing',
    'global-founders': 'Global Founders',
    'hack-week-hackathons-and-technical-events': 'Hack Week: Hackathons & Technical Events',
}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('fresh_path')
    ap.add_argument('--city', required=True, help='city slug, e.g. la')
    ap.add_argument('--name', required=True, help='display name, e.g. "Los Angeles"')
    ap.add_argument('--event', required=True, help='event title, e.g. "LA Tech Week 2026 (a16z Tech Week)"')
    ap.add_argument('--calendar-url', required=True)
    ap.add_argument('--core-dates', required=True, help='comma-separated YYYY-MM-DD list')
    args = ap.parse_args()

    with open(args.fresh_path, encoding='utf-8') as f:
        fresh = json.load(f)
    if isinstance(fresh, str):
        fresh = json.loads(fresh)
    if isinstance(fresh, dict):
        raw_events = fresh.get('events', [])
    else:
        raw_events = fresh

    events = []
    for e in raw_events:
        rec = {
            'id': e['id'],
            'name': e.get('name'),
            'host': e.get('host') or '',
            'cohosts': e.get('cohosts') or [],
            'sponsors': e.get('sponsors') or [],
            'date': e.get('date'),
            'time': e.get('time'),
            'neighborhood': e.get('neighborhood') or '',
            'tracks': e.get('tracks') or [],
            'featured': bool(e.get('featured')),
            'invite_only': bool(e.get('invite_only')),
            'registration_status': e.get('registration_status'),
            'techweek_url': e.get('techweek_url'),
            'end_time': None, 'start_utc': None, 'end_utc': None, 'approx_location': '',
            'rsvp_action': None, 'capacity': None, 'at_capacity': None, 'partiful_url': None,
            'description': '', 'detail_status': 'none', 'source': 'tech-week.com calendar',
        }
        events.append(rec)
    events.sort(key=lambda r: (r.get('date') or '', r.get('time') or ''))

    core_dates = args.core_dates.split(',')
    by_day = {}
    for e in events:
        if e.get('date'):
            by_day[e['date']] = by_day.get(e['date'], 0) + 1
    by_track = {}
    for e in events:
        for t in e.get('tracks') or []:
            by_track[t] = by_track.get(t, 0) + 1
    tracks_present = {k: TRACK_NAMES[k] for k in TRACK_NAMES if k in by_track}

    meta = {
        'city': args.name,
        'city_slug': args.city,
        'event': args.event,
        'calendar_url': args.calendar_url,
        'core_dates': core_dates,
        'scraped_at': str(date.today()),
        'timezone': 'America/Los_Angeles',
        'counts': {
            'events': len(events),
            'with_full_description': 0,
            'deleted_on_partiful': 0,
            'by_day': dict(sorted(by_day.items())),
            'by_track': dict(sorted(by_track.items(), key=lambda kv: -kv[1])),
        },
        'tracks': tracks_present,
        'pinned_events': [],
        'notes': [
            'Bootstrapped from a single calendar pull — every event has detail_status "none" '
            '(calendar metadata only: name, host, day, start time, neighborhood, tracks, featured flag).',
            'Open techweek_url (or find the Partiful page) and run scripts/partiful_extract.js for a '
            'full description, end time, RSVP type, and capacity on any specific event.',
            'registration_status comes from tech-week.com and can change daily; treat it as a hint, not truth.',
        ],
    }

    city_dir = os.path.join(ASSETS, args.city)
    os.makedirs(city_dir, exist_ok=True)
    with open(os.path.join(city_dir, 'events.json'), 'w', encoding='utf-8') as f:
        json.dump(events, f, ensure_ascii=False, indent=0)
    with open(os.path.join(city_dir, 'dataset.json'), 'w', encoding='utf-8') as f:
        json.dump(meta, f, indent=2)
    print(f'wrote {args.city}/events.json ({len(events)} events) + {args.city}/dataset.json')

    import subprocess
    import sys
    subprocess.run([sys.executable, os.path.join(HERE, 'build_index.py'), '--city', args.city], check=False)


if __name__ == '__main__':
    main()
