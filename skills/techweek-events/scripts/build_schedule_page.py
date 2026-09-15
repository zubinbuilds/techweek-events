#!/usr/bin/env python3
"""Render a curated Tech Week schedule as one self-contained, shareable HTML page.

This is the last step of the "recommend" flow: once a person has approved a
final list of events (with a one-line "why" per pick, same as the SKILL.md
output format), turn it into a page they can show someone else — "here's my
Tech Week schedule" — instead of a wall of chat text.

Input is a small JSON file (see assets/schedule-example.json for the shape):

{
  "title": "Ada's Tech Week Schedule",   # optional — auto-built from person.first_name if omitted
  "person": {"first_name": "Ada"},       # first name only; nothing else about the person goes on the page
  "days": [
    {"date": "2026-10-06", "label": "Tue Oct 6", "events": [
      {"time": "8:00–9:00am", "name": "...", "host": "...",
       "neighborhood": "Civic Center", "why": "...", "url": "https://..."}
    ]}
  ],
  "footer_note": "optional extra line, e.g. an event you deliberately left off"
}

Include a "date" (YYYY-MM-DD, within Oct 5-11) on each day so the week strip
at the top can highlight which days have plans; without it the strip still
renders from "label" but can't jump-link to the section.

This page is meant to be handed to other people, so it carries none of the
attendee's identifying details beyond a first name in the title — no last
name, company, title, or RSVP mechanics (application vs. instant RSVP,
waitlist status, etc.). It's just the plan: what, when, where, and why — no
separate summary line either; the event list speaks for itself. Each event's
name is the link (opens its Partiful/tech-week.com page); there's no separate
button.

Usage:
    python3 build_schedule_page.py schedule.json -o my-schedule.html

The output has no external CSS/JS (aside from a Google Fonts stylesheet) and
no tracking, so it works as-is:
  - pasted into Claude's Artifact tool (wrap or publish directly — see SKILL.md)
  - handed to ChatGPT to turn into a Site ("@Sites, publish this")
  - opened locally or emailed as a plain HTML attachment
"""
import argparse
import html
import json
import re
import sys

FONTS_LINK = (
    "<link rel='preconnect' href='https://fonts.googleapis.com'>"
    "<link rel='preconnect' href='https://fonts.gstatic.com' crossorigin>"
    "<link rel='stylesheet' href='https://fonts.googleapis.com/css2?"
    "family=Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700"
    "&family=Manrope:wght@500;600;700;800&display=swap'>"
)

# SF Tech Week 2026 runs Mon Oct 5 - Sun Oct 11. Fixed so the week strip can
# render every day (even ones with nothing planned) without guessing.
WEEK = [
    ("Mon", "05", "2026-10-05"), ("Tue", "06", "2026-10-06"), ("Wed", "07", "2026-10-07"),
    ("Thu", "08", "2026-10-08"), ("Fri", "09", "2026-10-09"), ("Sat", "10", "2026-10-10"),
    ("Sun", "11", "2026-10-11"),
]

CSS = """
:root {
  --bg: #f4f7f3; --bg2: #e6f0e6; --card: #ffffff; --ink: #16221a; --sub: #5d7264;
  --line: #dde6dc; --accent: #1f7a52; --accent-ink: #ffffff; --gold: #a8781f;
  --shadow: 0 1px 2px rgba(16,36,24,0.05), 0 8px 20px -10px rgba(16,36,24,0.14);
  --shadow-hover: 0 2px 4px rgba(16,36,24,0.07), 0 16px 30px -12px rgba(16,36,24,0.20);
  --serif: "Fraunces", Georgia, "Times New Roman", serif;
  --sans: "Manrope", -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
  padding-top: env(safe-area-inset-top, 0px);
  padding-bottom: env(safe-area-inset-bottom, 0px);
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #0e1712; --bg2: #132119; --card: #17251d; --ink: #edf3ee; --sub: #91a89a;
    --line: #263a2d; --accent: #52d394; --accent-ink: #08150e; --gold: #e2b768;
    --shadow: 0 1px 2px rgba(0,0,0,0.3), 0 8px 22px -10px rgba(0,0,0,0.5);
    --shadow-hover: 0 2px 4px rgba(0,0,0,0.35), 0 18px 32px -12px rgba(0,0,0,0.6);
  }
}
:root[data-theme="dark"] {
  --bg: #0e1712; --bg2: #132119; --card: #17251d; --ink: #edf3ee; --sub: #91a89a;
  --line: #263a2d; --accent: #52d394; --accent-ink: #08150e; --gold: #e2b768;
  --shadow: 0 1px 2px rgba(0,0,0,0.3), 0 8px 22px -10px rgba(0,0,0,0.5);
  --shadow-hover: 0 2px 4px rgba(0,0,0,0.35), 0 18px 32px -12px rgba(0,0,0,0.6);
}
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body {
  margin: 0; padding-block: 40px 64px; padding-inline: max(18px, env(safe-area-inset-left, 0px));
  background: linear-gradient(180deg, var(--bg2), var(--bg) 340px);
  color: var(--ink); font-family: var(--sans);
  line-height: 1.55; -webkit-font-smoothing: antialiased;
}
.wrap { max-width: 600px; margin: 0 auto; }
.eyebrow {
  font-size: 0.72rem; font-weight: 800; letter-spacing: 0.13em;
  text-transform: uppercase; color: var(--gold); margin: 0 0 12px;
}
header { margin-bottom: 8px; }
h1 {
  font-family: var(--serif); font-weight: 600; font-size: clamp(1.7rem, 6vw, 2.3rem); margin: 0;
  letter-spacing: -0.01em; text-wrap: balance; line-height: 1.12;
}

.week-strip {
  display: flex; gap: 8px; margin: 26px 0 32px; padding-bottom: 4px;
  overflow-x: auto; scrollbar-width: none; -webkit-overflow-scrolling: touch;
}
.week-strip::-webkit-scrollbar { display: none; }
.week-pill {
  flex: 0 0 auto; width: 46px; height: 56px; border-radius: 13px;
  border: 1px solid var(--line); background: var(--card);
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 2px; text-decoration: none; color: var(--sub);
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}
a.week-pill:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.week-pill .wd { font-size: 0.6rem; font-weight: 800; letter-spacing: 0.03em; text-transform: uppercase; }
.week-pill .wn { font-family: var(--serif); font-weight: 700; font-size: 1.1rem; color: var(--ink); line-height: 1; }
.week-pill.active { background: var(--accent); border-color: var(--accent); box-shadow: var(--shadow); }
.week-pill.active .wd, .week-pill.active .wn { color: var(--accent-ink); }
.week-pill.empty { opacity: 0.4; }
@media (hover: hover) {
  a.week-pill.active:hover { transform: translateY(-2px); box-shadow: var(--shadow-hover); }
}

.day { margin: 34px 0 0; scroll-margin-top: 16px; }
.day:first-of-type { margin-top: 0; }
.day-head { display: flex; align-items: baseline; gap: 10px; margin: 0 0 14px; padding-bottom: 10px; border-bottom: 2px solid var(--line); }
.day-head .day-num { font-family: var(--serif); font-weight: 700; font-size: 1.5rem; color: var(--gold); line-height: 1; }
.day-head .day-name { font-family: var(--serif); font-weight: 600; font-style: italic; font-size: 1.12rem; color: var(--ink); }

.cards { display: flex; flex-direction: column; gap: 10px; }
.card {
  position: relative; background: var(--card); border: 1px solid var(--line); border-radius: 14px;
  padding: 15px 18px 15px 22px; box-shadow: var(--shadow);
  transition: box-shadow 0.18s ease, transform 0.18s ease;
}
.card::before {
  content: ""; position: absolute; left: 0; top: 12px; bottom: 12px; width: 4px;
  border-radius: 4px; background: var(--accent);
}
@media (hover: hover) {
  .card:hover { box-shadow: var(--shadow-hover); transform: translateY(-1px); }
}
.card .time {
  font-size: 0.78rem; color: var(--accent); white-space: nowrap; font-weight: 700;
  font-variant-numeric: tabular-nums; letter-spacing: 0.02em; display: block; margin-bottom: 6px;
}
.card .name {
  font-family: var(--serif); font-weight: 600; font-size: 1.15rem; margin: 0 0 4px;
  text-wrap: balance; line-height: 1.28;
}
.card .name a {
  color: var(--ink); text-decoration: none;
  background-image: linear-gradient(var(--accent), var(--accent));
  background-repeat: no-repeat; background-position: 0 100%; background-size: 0% 2px;
  transition: background-size 0.2s ease; padding-bottom: 1px;
}
@media (hover: hover) {
  .card .name a:hover { background-size: 100% 2px; }
}
.card .name a:focus-visible { outline: 2px solid var(--accent); outline-offset: 3px; }
.card .name .ext { color: var(--accent); font-weight: 700; font-size: 0.8em; margin-left: 1px; }
.card .meta { font-size: 0.85rem; color: var(--sub); margin-bottom: 8px; }
.card .why { font-size: 0.93rem; margin: 8px 0 0; }

footer {
  margin-top: 44px; padding-top: 18px; border-top: 1px solid var(--line);
  font-size: 0.82rem; color: var(--sub);
}
footer p { margin: 0 0 4px; }
footer a { color: var(--accent); text-decoration: none; font-weight: 700; }
footer a:hover, footer a:focus-visible { text-decoration: underline; }
:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
@media (max-width: 400px) {
  h1 { font-size: 1.55rem; }
  .card { padding: 13px 15px 13px 19px; }
}
@media (prefers-reduced-motion: reduce) {
  * { transition: none !important; animation: none !important; }
  .card:hover, a.week-pill:hover { transform: none !important; }
}
"""


def esc(s):
    return html.escape(str(s), quote=True) if s is not None else ""


def day_date(day: dict):
    d = day.get("date")
    if d:
        return d
    label = day.get("label") or ""
    m = re.search(r"(\d{1,2})\s*$", label.strip())
    if not m:
        return None
    num = m.group(1).zfill(2)
    for _, dom, iso in WEEK:
        if dom == num:
            return iso
    return None


def render(data: dict) -> str:
    person = data.get("person") or {}
    first_name = person.get("first_name")
    title = data.get("title") or (f"{first_name}'s Tech Week Schedule" if first_name else "My Tech Week Schedule")
    footer_note = data.get("footer_note")
    days = data.get("days", [])

    present_dates = {day_date(d) for d in days if day_date(d)}

    parts = []
    parts.append("<!doctype html><html lang='en'><head><meta charset='utf-8'>")
    parts.append("<meta name='viewport' content='width=device-width, initial-scale=1, viewport-fit=cover'>")
    parts.append(f"<title>{esc(title)}</title>{FONTS_LINK}<style>{CSS}</style></head><body><div class='wrap'>")
    parts.append("<header>")
    parts.append("<p class='eyebrow'>SF Tech Week 2026 · Oct 5&ndash;11</p>")
    parts.append(f"<h1>{esc(title)}</h1>")
    parts.append("</header>")

    parts.append("<nav class='week-strip' aria-label='Days'>")
    for dow, dom, iso in WEEK:
        if iso in present_dates:
            parts.append(f"<a class='week-pill active' href='#d-{iso}'><span class='wd'>{dow}</span><span class='wn'>{dom}</span></a>")
        else:
            parts.append(f"<span class='week-pill empty'><span class='wd'>{dow}</span><span class='wn'>{dom}</span></span>")
    parts.append("</nav>")

    for day in days:
        label = day.get("label") or day.get("date") or ""
        iso = day_date(day)
        day_num = next((dom for _, dom, i in WEEK if i == iso), "")
        if not day_num:
            m = re.search(r"(\d{1,2})\s*$", label.strip())
            day_num = m.group(1).zfill(2) if m else ""
        anchor = f" id='d-{iso}'" if iso else ""
        parts.append(f"<section class='day'{anchor}>")
        parts.append(
            f"<div class='day-head'><span class='day-num'>{esc(day_num)}</span>"
            f"<span class='day-name'>{esc(label)}</span></div>"
        )
        parts.append("<div class='cards'>")
        for ev in day.get("events", []):
            parts.append("<div class='card'>")
            parts.append(f"<span class='time'>{esc(ev.get('time', ''))}</span>")
            name = esc(ev.get("name", ""))
            if ev.get("url"):
                parts.append(
                    f"<h3 class='name'><a href='{esc(ev['url'])}' target='_blank' rel='noopener'>"
                    f"{name}<span class='ext' aria-hidden='true'>&nearr;</span></a></h3>"
                )
            else:
                parts.append(f"<h3 class='name'>{name}</h3>")
            meta_bits = [b for b in [ev.get("host"), ev.get("neighborhood")] if b]
            if meta_bits:
                parts.append(f"<div class='meta'>{esc(' · '.join(meta_bits))}</div>")
            if ev.get("why"):
                parts.append(f"<div class='why'>{esc(ev['why'])}</div>")
            parts.append("</div>")
        parts.append("</div></section>")

    parts.append("<footer>")
    if footer_note:
        parts.append(f"<p>{esc(footer_note)}</p>")
    parts.append(
        "<p>Built for SF Tech Week 2026 with the "
        "<a href='https://github.com/zubinbuilds/techweek-events' target='_blank' rel='noopener'>techweek-events</a> "
        "Agent Skill.</p>"
    )
    parts.append("</footer></div></body></html>")
    return "".join(parts)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("schedule_json", help="path to the curated schedule JSON (see assets/schedule-example.json)")
    ap.add_argument("-o", "--out", default="schedule.html", help="output HTML path (default: schedule.html)")
    args = ap.parse_args()

    with open(args.schedule_json, encoding="utf-8") as f:
        data = json.load(f)

    out_html = render(data)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(out_html)
    print(f"wrote {args.out} ({len(out_html)} chars)", file=sys.stderr)


if __name__ == "__main__":
    main()
