#!/usr/bin/env python3
"""Regenerate assets/<city>/events-index.md (the no-code, one-line-per-event
view) from assets/<city>/events.json. Run after merge_refresh.py --write or
bootstrap_city.py. Defaults to --city sf."""
import argparse
import json
import os
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(os.path.dirname(HERE), 'assets')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--city', default='sf')
    args = ap.parse_args()
    city_dir = os.path.join(ASSETS, args.city)
    events = json.load(open(os.path.join(city_dir, 'events.json'), encoding='utf-8'))
    meta = json.load(open(os.path.join(city_dir, 'dataset.json'), encoding='utf-8'))
    pinned = [e for e in events if e.get('pinned')]
    rest = [e for e in events if not e.get('pinned')]
    by_day = Counter(e['date'] for e in rest)
    lines = [f"# {meta.get('city', args.city.upper())} Tech Week 2026 — event index", '',
             f"Generated from tech-week.com on {meta['scraped_at']}. {len(rest)} events. "
             'Format: `time | name | host | tracks | neighborhood | flags | url`. '
             'Flags: F=featured, D=full description available in events.json, C=closed registration, X=removed from calendar.', '']
    if pinned:
        lines += ['## Pinned (skill author)', '']
        for e in pinned:
            lines.append(f"* all week | {e['name']} | {e['host']} ({', '.join(e.get('cohosts') or [])}) | {','.join(e['tracks'])} | citywide | D | {e['partiful_url']}")
        lines.append('')
    for day in sorted(by_day):
        lines += [f'## {day} ({by_day[day]} events)', '']
        for e in sorted([x for x in rest if x['date'] == day], key=lambda x: x.get('time') or ''):
            flags = ''.join(['F' if e.get('featured') else '', 'D' if e.get('detail_status') == 'full' else '',
                             'C' if e.get('registration_status') == 'closed' else '',
                             'X' if e.get('registration_status') == 'removed' else '']) or '-'
            url = e.get('partiful_url') or e.get('techweek_url')
            lines.append(f"* {e.get('time')} | {e['name']} | {e.get('host')} | {','.join(e.get('tracks') or []) or '-'} | {e.get('neighborhood') or '-'} | {flags} | {url}")
        lines.append('')
    with open(os.path.join(city_dir, 'events-index.md'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f'wrote {args.city}/events-index.md ({len(rest)} events, {len(pinned)} pinned)')


if __name__ == '__main__':
    main()
