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
  "note": "One or two sentences on the shape of the week.",   # optional
  "days": [
    {"label": "Tue Oct 6", "events": [
      {"time": "8:00–9:00am", "name": "...", "host": "...",
       "neighborhood": "Civic Center", "why": "...", "url": "https://..."}
    ]}
  ],
  "footer_note": "optional extra line"
}

This page is meant to be handed to other people, so it carries none of the
attendee's identifying details beyond a first name in the title — no last
name, company, title, or RSVP mechanics (application vs. instant RSVP,
waitlist status, etc.). It's just the plan: what, when, where, and why.

Usage:
    python3 build_schedule_page.py schedule.json -o my-schedule.html

The output has no external CSS/JS and no network calls, so it works as-is:
  - pasted into Claude's Artifact tool (wrap or publish directly — see SKILL.md)
  - handed to ChatGPT to turn into a Site ("@Sites, publish this")
  - opened locally or emailed as a plain HTML attachment
"""
import argparse
import html
import json
import sys

FONTS_LINK = (
    "<link rel='preconnect' href='https://fonts.googleapis.com'>"
    "<link rel='preconnect' href='https://fonts.gstatic.com' crossorigin>"
    "<link rel='stylesheet' href='https://fonts.googleapis.com/css2?"
    "family=Fraunces:opsz,wght@9..144,500;9..144,600&family=Source+Sans+3:wght@400;600;700&display=swap'>"
)

CSS = """
:root {
  --bg: #f4f3fa; --bg2: #eceafb; --card: #ffffff; --ink: #16151f; --sub: #6b6879;
  --line: #e2dfee; --accent: #3733e0; --accent-ink: #ffffff;
  --shadow: 0 1px 2px rgba(29,23,68,0.04), 0 6px 16px -8px rgba(29,23,68,0.10);
  --shadow-hover: 0 2px 4px rgba(29,23,68,0.06), 0 14px 28px -10px rgba(29,23,68,0.16);
  --serif: "Fraunces", Georgia, "Times New Roman", serif;
  --sans: "Source Sans 3", -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
  padding-top: env(safe-area-inset-top, 0px);
  padding-bottom: env(safe-area-inset-bottom, 0px);
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #131220; --bg2: #191830; --card: #1c1b2c; --ink: #eeecf7; --sub: #a29dbd;
    --line: #2e2b45; --accent: #9a95ff; --accent-ink: #131220;
    --shadow: 0 1px 2px rgba(0,0,0,0.25), 0 6px 18px -8px rgba(0,0,0,0.45);
    --shadow-hover: 0 2px 4px rgba(0,0,0,0.3), 0 16px 30px -10px rgba(0,0,0,0.55);
  }
}
:root[data-theme="dark"] {
  --bg: #131220; --bg2: #191830; --card: #1c1b2c; --ink: #eeecf7; --sub: #a29dbd;
  --line: #2e2b45; --accent: #9a95ff; --accent-ink: #131220;
  --shadow: 0 1px 2px rgba(0,0,0,0.25), 0 6px 18px -8px rgba(0,0,0,0.45);
  --shadow-hover: 0 2px 4px rgba(0,0,0,0.3), 0 16px 30px -10px rgba(0,0,0,0.55);
}
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body {
  margin: 0; padding-block: 40px 64px; padding-inline: max(18px, env(safe-area-inset-left, 0px));
  background: linear-gradient(180deg, var(--bg2), var(--bg) 320px);
  color: var(--ink); font-family: var(--sans);
  line-height: 1.55; -webkit-font-smoothing: antialiased;
}
.wrap { max-width: 600px; margin: 0 auto; }
.eyebrow {
  font-family: var(--sans); font-size: 0.72rem; font-weight: 700; letter-spacing: 0.13em;
  text-transform: uppercase; color: var(--accent); margin: 0 0 12px;
}
header { margin-bottom: 30px; }
h1 {
  font-family: var(--serif); font-weight: 600; font-size: clamp(1.7rem, 6vw, 2.3rem); margin: 0 0 8px;
  letter-spacing: -0.01em; text-wrap: balance; line-height: 1.12;
}
.note { font-size: 1rem; margin: 0; max-width: 60ch; color: var(--ink); opacity: 0.88; }
.day { margin: 30px 0 0; }
.day:first-of-type { margin-top: 6px; }
.day h2 {
  font-family: var(--serif); font-weight: 600; font-size: 1.1rem; font-style: italic;
  color: var(--ink); margin: 0 0 12px; padding-bottom: 8px; border-bottom: 1px solid var(--line);
}
.cards { display: flex; flex-direction: column; gap: 10px; }
.card {
  background: var(--card); border: 1px solid var(--line); border-radius: 16px;
  padding: 16px 18px; box-shadow: var(--shadow);
  transition: box-shadow 0.18s ease, transform 0.18s ease;
}
@media (hover: hover) {
  .card:hover { box-shadow: var(--shadow-hover); transform: translateY(-1px); }
}
.card .time {
  font-size: 0.78rem; color: var(--accent); white-space: nowrap; font-weight: 700;
  font-variant-numeric: tabular-nums; letter-spacing: 0.02em; display: block; margin-bottom: 6px;
}
.card .name { font-weight: 700; font-size: 1.06rem; margin: 0 0 3px; text-wrap: balance; line-height: 1.3; }
.card .meta { font-size: 0.85rem; color: var(--sub); margin-bottom: 8px; }
.card .why { font-size: 0.93rem; margin: 8px 0 12px; }
.card a.link {
  display: inline-flex; align-items: center; gap: 5px;
  font-size: 0.84rem; font-weight: 700; text-decoration: none;
  color: var(--accent); border: 1.5px solid var(--accent); border-radius: 999px;
  padding: 7px 14px; min-height: 32px; transition: background 0.15s ease, color 0.15s ease;
}
@media (hover: hover) {
  .card a.link:hover { background: var(--accent); color: var(--accent-ink); }
}
.card a.link:active { background: var(--accent); color: var(--accent-ink); }
.card a.link:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
footer {
  margin-top: 40px; padding-top: 18px; border-top: 1px solid var(--line);
  font-size: 0.82rem; color: var(--sub);
}
footer p { margin: 0 0 4px; }
footer a { color: var(--accent); text-decoration: none; font-weight: 600; }
footer a:hover, footer a:focus-visible { text-decoration: underline; }
:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
@media (max-width: 400px) {
  h1 { font-size: 1.55rem; }
  .card { padding: 14px 15px; border-radius: 14px; }
}
@media (prefers-reduced-motion: reduce) {
  * { transition: none !important; animation: none !important; }
  .card:hover { transform: none !important; }
}
"""


def esc(s):
    return html.escape(str(s), quote=True) if s is not None else ""


def render(data: dict) -> str:
    person = data.get("person") or {}
    first_name = person.get("first_name")
    title = data.get("title") or (f"{first_name}'s Tech Week Schedule" if first_name else "My Tech Week Schedule")
    note = data.get("note")
    footer_note = data.get("footer_note")

    parts = []
    parts.append("<!doctype html><html lang='en'><head><meta charset='utf-8'>")
    parts.append("<meta name='viewport' content='width=device-width, initial-scale=1, viewport-fit=cover'>")
    parts.append(f"<title>{esc(title)}</title>{FONTS_LINK}<style>{CSS}</style></head><body><div class='wrap'>")
    parts.append("<header>")
    parts.append("<p class='eyebrow'>SF Tech Week 2026 · Oct 5&ndash;11</p>")
    parts.append(f"<h1>{esc(title)}</h1>")
    if note:
        parts.append(f"<p class='note'>{esc(note)}</p>")
    parts.append("</header>")

    for day in data.get("days", []):
        label = day.get("label") or day.get("date") or ""
        parts.append(f"<section class='day'><h2>{esc(label)}</h2><div class='cards'>")
        for ev in day.get("events", []):
            parts.append("<div class='card'>")
            parts.append(f"<span class='time'>{esc(ev.get('time', ''))}</span>")
            parts.append(f"<div class='name'>{esc(ev.get('name', ''))}</div>")
            meta_bits = [b for b in [ev.get("host"), ev.get("neighborhood")] if b]
            if meta_bits:
                parts.append(f"<div class='meta'>{esc(' · '.join(meta_bits))}</div>")
            if ev.get("why"):
                parts.append(f"<div class='why'>{esc(ev['why'])}</div>")
            if ev.get("url"):
                parts.append(f"<a class='link' href='{esc(ev['url'])}' target='_blank' rel='noopener'>View on Partiful →</a>")
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
