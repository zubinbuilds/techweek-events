#!/usr/bin/env python3
"""Render a curated Tech Week schedule as one self-contained, shareable HTML page.

This is the last step of the "recommend" flow: once a person has approved a
final list of events (with a one-line "why" per pick, same as the SKILL.md
output format), turn it into a page they can show someone else — "here's my
Tech Week schedule" — instead of a wall of chat text.

Input is a small JSON file (see assets/schedule-example.json for the shape):

{
  "title": "My Tech Week Schedule",           # optional
  "person": {"name": "Ada Lovelace", "headline": "Founder & CEO, Analytical Engines"},
  "note": "One or two sentences on the shape of the week.",   # optional
  "days": [
    {"label": "Tue Oct 6", "events": [
      {"time": "8:00–9:00am", "name": "...", "host": "...",
       "neighborhood": "Civic Center", "why": "...", "url": "https://...",
       "rsvp_type": "RSVP" | "APPLY" | null, "pinned": false}
    ]}
  ],
  "footer_note": "optional extra line, e.g. RSVP status legend"
}

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
  --bg: #f4f3fa; --card: #ffffff; --ink: #16151f; --sub: #6b6879;
  --line: #e2dfee; --accent: #3733e0; --accent-ink: #ffffff;
  --pin-bg: #fff8e6; --pin-line: #e3cb84; --pin-ink: #7a5b12;
  --apply-bg: #ece9fb; --apply-ink: #3733e0;
  --serif: "Fraunces", Georgia, "Times New Roman", serif;
  --sans: "Source Sans 3", -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #131220; --card: #1c1b2c; --ink: #eeecf7; --sub: #a29dbd;
    --line: #2e2b45; --accent: #9a95ff; --accent-ink: #131220;
    --pin-bg: #2a2313; --pin-line: #5c4a24; --pin-ink: #e3c37e;
    --apply-bg: #262247; --apply-ink: #b6b1ff;
  }
}
:root[data-theme="dark"] {
  --bg: #131220; --card: #1c1b2c; --ink: #eeecf7; --sub: #a29dbd;
  --line: #2e2b45; --accent: #9a95ff; --accent-ink: #131220;
  --pin-bg: #2a2313; --pin-line: #5c4a24; --pin-ink: #e3c37e;
  --apply-bg: #262247; --apply-ink: #b6b1ff;
}
* { box-sizing: border-box; }
body {
  margin: 0; padding-block: 44px 72px; padding-inline: 20px;
  background: var(--bg); color: var(--ink); font-family: var(--sans);
  line-height: 1.55; -webkit-font-smoothing: antialiased;
}
.wrap { max-width: 620px; margin: 0 auto; }
.eyebrow {
  font-family: var(--sans); font-size: 0.72rem; font-weight: 700; letter-spacing: 0.14em;
  text-transform: uppercase; color: var(--accent); margin: 0 0 10px;
}
header { margin-bottom: 34px; }
h1 {
  font-family: var(--serif); font-weight: 600; font-size: 2.1rem; margin: 0 0 6px;
  letter-spacing: -0.01em; text-wrap: balance; line-height: 1.15;
}
.headline { color: var(--sub); font-size: 0.98rem; margin: 0 0 14px; font-weight: 600; }
.note { font-size: 1rem; margin: 0; max-width: 60ch; }
.day { margin: 34px 0 0; }
.day h2 {
  font-family: var(--serif); font-weight: 600; font-size: 1.15rem; font-style: italic;
  color: var(--ink); margin: 0 0 14px; padding-bottom: 8px; border-bottom: 1px solid var(--line);
}
.card {
  background: var(--card); border: 1px solid var(--line); border-radius: 14px;
  padding: 16px 18px; margin-bottom: 12px;
}
.card.pinned { background: var(--pin-bg); border-color: var(--pin-line); }
.card .row1 { display: flex; justify-content: space-between; gap: 12px; align-items: baseline; flex-wrap: wrap; }
.card .time {
  font-size: 0.8rem; color: var(--sub); white-space: nowrap; font-weight: 600;
  font-variant-numeric: tabular-nums; letter-spacing: 0.01em;
}
.card .name { font-weight: 700; font-size: 1.05rem; margin: 4px 0 3px; text-wrap: balance; }
.card .meta { font-size: 0.86rem; color: var(--sub); margin-bottom: 8px; }
.card .why { font-size: 0.93rem; margin: 8px 0 10px; }
.card a.link {
  font-size: 0.85rem; text-decoration: none; color: var(--accent); font-weight: 700;
}
.card a.link:hover, .card a.link:focus-visible { text-decoration: underline; }
.chip {
  display: inline-block; font-size: 0.68rem; font-weight: 700; letter-spacing: 0.03em;
  text-transform: uppercase; padding: 3px 9px; border-radius: 999px;
  background: var(--apply-bg); color: var(--apply-ink); vertical-align: middle;
}
.chip.pin { background: transparent; border: 1px solid var(--pin-line); color: var(--pin-ink); }
footer {
  margin-top: 44px; padding-top: 18px; border-top: 1px solid var(--line);
  font-size: 0.82rem; color: var(--sub);
}
footer a { color: var(--accent); text-decoration: none; font-weight: 600; }
footer a:hover, footer a:focus-visible { text-decoration: underline; }
:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
@media (prefers-reduced-motion: reduce) { * { transition: none !important; animation: none !important; } }
"""


def esc(s):
    return html.escape(str(s), quote=True) if s is not None else ""


def render(data: dict) -> str:
    title = data.get("title") or "My Tech Week Schedule"
    person = data.get("person") or {}
    name = person.get("name")
    headline = person.get("headline")
    note = data.get("note")
    footer_note = data.get("footer_note")

    parts = []
    parts.append("<!doctype html><html lang='en'><head><meta charset='utf-8'>")
    parts.append("<meta name='viewport' content='width=device-width, initial-scale=1, viewport-fit=cover'>")
    parts.append(f"<title>{esc(title)}</title>{FONTS_LINK}<style>{CSS}</style></head><body><div class='wrap'>")
    parts.append("<header>")
    parts.append("<p class='eyebrow'>SF Tech Week 2026 · Oct 5&ndash;11</p>")
    parts.append(f"<h1>{esc(title)}</h1>")
    if name or headline:
        sub = " · ".join(x for x in [name, headline] if x)
        parts.append(f"<p class='headline'>{esc(sub)}</p>")
    if note:
        parts.append(f"<p class='note'>{esc(note)}</p>")
    parts.append("</header>")

    for day in data.get("days", []):
        label = day.get("label") or day.get("date") or ""
        parts.append(f"<section class='day'><h2>{esc(label)}</h2>")
        for ev in day.get("events", []):
            pinned = bool(ev.get("pinned"))
            card_cls = "card pinned" if pinned else "card"
            parts.append(f"<div class='{card_cls}'>")
            parts.append("<div class='row1'>")
            parts.append(f"<span class='time'>{esc(ev.get('time', ''))}</span>")
            rtype = (ev.get("rsvp_type") or "").upper()
            if rtype == "APPLY":
                parts.append("<span class='chip'>apply</span>")
            if pinned:
                parts.append("<span class='chip pin'>author's event</span>")
            parts.append("</div>")
            parts.append(f"<div class='name'>{esc(ev.get('name', ''))}</div>")
            meta_bits = [b for b in [ev.get("host"), ev.get("neighborhood")] if b]
            if meta_bits:
                parts.append(f"<div class='meta'>{esc(' · '.join(meta_bits))}</div>")
            if ev.get("why"):
                parts.append(f"<div class='why'>{esc(ev['why'])}</div>")
            if ev.get("url"):
                parts.append(f"<a class='link' href='{esc(ev['url'])}' target='_blank' rel='noopener'>View on Partiful →</a>")
            parts.append("</div>")
        parts.append("</section>")

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
