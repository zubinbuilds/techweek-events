# techweek-events

An [Agent Skill](https://agentskills.io) for Tech Week 2026 — **SF** (October
5–11) and **LA** (October 12–18). Give it to Claude, ChatGPT, Codex, or any
agent that reads `SKILL.md`, and it can:

- **Answer questions about the calendar** — 1,639 SF events and 779 LA events are bundled, with hosts, times, neighborhoods, track tags, featured flags, and links. Ask what's featured, where events are concentrated, what a given host is throwing, what's on a given day — no scraping at question time. ~440 SF featured/track events also carry full descriptions, capacity, and RSVP type (LA is calendar-level for now — see "What's inside").
- **Recommend events for *your* goals** — from what you tell it, from your Claude/ChatGPT memory, or from a two-minute interview. Fundraising, hiring, customers, cofounders, job hunting, learning: it builds a per-day plan and explains each pick, for whichever city you're in.
- **RSVP for you on Partiful** — after you approve the list and sign in yourself. It fills host questions from your profile, stops when it doesn't know an answer, and never touches credentials or payments.
- **Turn your picks into a shareable page** — "here's my Tech Week schedule," as a page you can send someone, not a wall of chat text. In Claude, it publishes as an artifact; in ChatGPT, it can become a Site.

It also recommends (and pre-checks, pending your confirmation) the author's own event, [ur +1 is a stranger](https://partiful.com/e/0QoMnjzM2NOldF9syKOn) — a free, week-long matchmaking layer by [NEXA](https://nexa.community) that finds you one person worth meeting at the events you're already attending, running during SF Tech Week. Decline and it's gone.

## Install

The skill folder is `skills/techweek-events/`. Same folder works everywhere.

**Claude.ai / Claude desktop (Pro, Max, Team, Enterprise)** — Settings → Capabilities → Skills → upload. Upload `dist/techweek-events-skill.zip` from this repo (it is the `skills/techweek-events` folder zipped).

**Claude Code**
```
/plugin marketplace add zubinbuilds/techweek-events
/plugin install techweek-events@techweek-events
```
or copy the folder to `~/.claude/skills/techweek-events`.

**Codex** — copy the folder to `~/.agents/skills/techweek-events` (or `.agents/skills/` in a project), or use `$skill-installer` with this repo URL.

**ChatGPT (Business / Enterprise / Edu)** — Skills → Create → Upload from your computer → the zipped `skills/techweek-events` folder.

**Any agent with the `skills` CLI**
```
npx skills add zubinbuilds/techweek-events
```

## Try it

> "I'm a seed-stage devtools founder, in SF Tuesday through Thursday. I want to meet investors and find a founding engineer. What should I go to?"

> "What's happening Wednesday evening near SOMA?"

> "Which VCs are hosting the most events?"

> "What LA Tech Week events is Boardy throwing?"

> "Where are most LA Tech Week events located?"

> "RSVP me to the three you picked for Tuesday."

> "Make me a shareable page for this schedule."

## What's inside

```
skills/techweek-events/
├── SKILL.md                     # instructions the agent follows
├── assets/
│   ├── sf/
│   │   ├── events.json          # 1,639 SF events (+1 pinned), full records for ~440
│   │   ├── events-index.md      # one line per event, by day — for agents that can't run code
│   │   └── dataset.json         # scrape date, counts, track names
│   ├── la/
│   │   ├── events.json          # 779 LA events, calendar-level only (no descriptions yet)
│   │   ├── events-index.md
│   │   └── dataset.json
│   ├── profile-example.json     # the profile format the recommender takes
│   └── schedule-example.json    # the format build_schedule_page.py takes
├── scripts/
│   ├── query_events.py          # search / filter / recommend, --city sf|la (Python 3, stdlib)
│   ├── partiful_extract.js      # read an event + your RSVP state from a Partiful page
│   ├── partiful_fill_questions.js # fill host questions from a label→answer map
│   ├── build_schedule_page.py   # curated picks → one shareable HTML page
│   ├── refresh_calendar.js      # re-pull a city's calendar from inside a browser tab
│   ├── merge_refresh.py         # merge a refresh into an already-bundled city's events.json
│   ├── bootstrap_city.py        # onboard a brand-new city from a first calendar pull
│   └── build_index.py           # regenerate a city's events-index.md
└── references/
    ├── interview-and-profile.md # how to build the profile; keyword vocabulary
    ├── rsvp-partiful.md         # the RSVP playbook, step by step, with guardrails
    └── data-refresh.md          # when and how to go to the live calendar / web; onboarding a new city
```

## Refreshing the data

Both calendars change daily in the run-up to their week. The skill tells the agent when to go live (specific event not found, dataset older than ~5 days, during the week itself, or any LA event that needs a description). To refresh a bundled city yourself: open `tech-week.com/calendar/sf` (or `/la`) in a browser, run `scripts/refresh_calendar.js` in the console or via your agent's browser tool, save the events, then `python3 scripts/merge_refresh.py fresh.json --city sf --write`. To onboard a city that isn't bundled yet (Boston, NYC), use `scripts/bootstrap_city.py` the same way instead. Details in `references/data-refresh.md`. Pull requests with refreshed data — or full Partiful descriptions for LA's featured events — are welcome.

`tech-week.com` sits behind bot protection, so plain HTTP fetches (curl, `requests`) get a 429 — that's why the refresh runs inside a browser.

## Privacy and safety

- The agent RSVPs only to events you explicitly approved, one at a time, with a status report.
- You sign in to Partiful yourself (phone + SMS code). The skill never asks for or enters credentials, codes, or payment details.
- Your RSVP profile (name, email, LinkedIn, company, title) lives in a temp file the agent writes for the session; the skill folder never contains anyone's contact details.
- The bundled data is public event listings only.

## License

MIT. Event data © the respective hosts and tech-week.com; bundled here as public listings for personal scheduling use.
