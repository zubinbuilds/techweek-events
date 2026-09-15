# When the bundled data isn't enough, and how to go to the web

## What's in the dataset (and what isn't)

`assets/sf/events.json` and `assets/la/events.json` — every event on the
tech-week.com calendar for that city as of the `scraped_at` date in its
`dataset.json` (run `query_events.py cities` for both at a glance, or
`stats --city <city>` for one).

| you have, for every event in both cities | you have only for each city's "priority" events (~440 SF, 120 of 121 LA) | you don't have |
|---|---|---|
| name, host, co-hosts, sponsors | full description (~900 chars) | events added after `scraped_at` |
| day, start time, neighborhood | end time, exact venue neighborhood | events that were removed or rescheduled since |
| track tags, featured flag | RSVP type (RSVP vs APPLY), capacity, at-capacity | live capacity / waitlist state |
| registration status (as of scrape) | Partiful URL | descriptions for SF's other ~1,200 or LA's other ~660 non-priority events |
| tech-week.com redirect link | | Boston / NYC Tech Week (not bundled at all) |
| | | which events sell tickets (Partiful hides pricing from the calendar; `partiful_extract.js` reports `ticketed`) |

Each city's "priority" events are the featured and track-tagged ones —
that's where the substantive programming is; the remaining events are
dominated by run clubs, coffee meetups, and small mixers, searchable by
name and host but you'd have to open one to know more. SF has ~440 detailed
priority events; LA has 120 of its 121 priority events fully detailed
(walked event-by-event on Partiful the same way SF was) — the 1 exception
is `fab5528b-dd6f-49b7-a127-a19ae6dd9c1c` ("Securing the Future: Investing
in America's Critical Industries"), whose techweek_url redirects to a
Partiful page that returns "Not Found"; it's marked
`detail_status: "deleted"` and stays calendar-level. Every non-priority
event in both cities is calendar-level only: name, host, day, time,
neighborhood, tracks, featured flag. Open specific calendar-level events
live (below) before recommending or RSVPing anyone to them.

## When to go live

- The user asks about **a specific event** you can't find by name or host →
  it's new or renamed. Check the calendar.
- The user is asking **during Tech Week** (SF: Oct 5–11, LA: Oct 12–18) or
  within a few days before it → registration states and capacities have
  moved. Refresh, or at least open the specific events you're about to
  recommend.
- `scraped_at` is **more than ~5 days old** and the user wants a plan → refresh.
- A goal has **no strong matches** → the answer may be in an event without a
  description. Open the top few candidates from `search` and read them.
- **Any calendar-level event** (non-priority in either city, or LA's one
  broken-link event) you're about to recommend or RSVP someone to → open it
  live first (see below) to get a description, RSVP type, and capacity —
  the bundled data doesn't have these for calendar-level events.
- The user asks about **Boston or NYC Tech Week** → not bundled. Same
  scripts work; see "Onboarding a new city" below.
- The user asks about **official a16z programming, speakers, or news** → web
  search; the calendar doesn't carry that.

## Live lookups, cheapest first

**One event's full details** — navigate to its `partiful_url` (or
`techweek_url`, which redirects) and execute `scripts/partiful_extract.js`.
Returns description, capacity, RSVP type, host questions, and whether the
current browser session is signed in / already RSVP'd. ~2s per event. To fetch
descriptions for a handful of lightweight events, do this in a loop (batch
10–12 per call if your browser tool supports batching) and write the results
back into `events.json` under `description`, `end_time`, `rsvp_action`,
`capacity`, `at_capacity`, `partiful_url`, and set `detail_status: "full"`.

**Search the live calendar by keyword** — from a tab on
`https://www.tech-week.com/calendar/sf` (or `/calendar/la`), run:

```js
await (await fetch('/api/trpc/calendar.events?batch=1', {method:'POST',
  headers:{'content-type':'application/json'},
  body: JSON.stringify({"0":{city:"sf",q:"<keywords>",featured:false,track:[],sponsor:[],theme:[],
    format:[],location:[],time:[],host:[],sortBy:"time",sortOrder:"asc",cursor:1,direction:"forward"}})
})).json()
```

Set `city` to match the tab you're on (`"sf"` or `"la"`). `[0].result.data.results`
is a page of 48 events (`total` tells you how many match). Filter by
`track: ["fintech"]`, or by `day` if the site exposes it (check the request
the page itself makes when you click a day tab).

**Full refresh of a city already bundled** — from a tab on that city's
calendar, execute `scripts/refresh_calendar.js` (strip comment lines if your
tool has a payload limit; it reads the city from the URL automatically). It
pulls every page plus the nine track queries (~15–40s for SF, ~10s for LA)
into `window.__twRefresh` and returns a summary. Pull the events out in
slices of ~400 (`JSON.stringify(window.__twRefresh.events.slice(0,400))`,
then 400–800, …) — a tool that hits a payload/token limit on `JSON.stringify`
usually still saves the full result to a local file; if so, JSON-parse that
file directly instead of retrying with smaller slices. Save each slice,
concatenate into one JSON array, then:

```
python3 scripts/merge_refresh.py fresh.json --city sf          # preview: added / changed / removed
python3 scripts/merge_refresh.py fresh.json --city sf --write  # apply, and rebuild events-index.md
```

(`--city` defaults to `sf`; pass `--city la` for LA.) The merge keeps
Partiful-sourced fields, updates calendar fields, adds new events with
`detail_status: "none"`, and marks vanished ones `registration_status:
"removed"`.

## Onboarding a new city (Boston, NYC)

Same calendar, same tRPC API, just a different `city` slug and URL path —
this is exactly how LA went from "not bundled" to bundled. From a tab on
`https://www.tech-week.com/calendar/<slug>` (`boston`, `nyc`), run
`scripts/refresh_calendar.js`, pull the events out in slices the same way as
a refresh, concatenate them, then bootstrap instead of merge (there's nothing
to merge against yet):

```
python3 scripts/bootstrap_city.py fresh.json --city nyc --name "New York" \
  --event "NYC Tech Week 2026 (a16z Tech Week)" \
  --calendar-url https://www.tech-week.com/calendar/nyc \
  --core-dates 2026-06-01,2026-06-02,2026-06-03,2026-06-04,2026-06-05,2026-06-06,2026-06-07
```

Check `tech-week.com`'s own homepage for each city's actual date range before
running this — they move year to year. This writes
`assets/nyc/{events.json,dataset.json,events-index.md}` with every event at
`detail_status: "none"` (calendar-level only — bootstrap first, then walk
priority events on Partiful the way SF and LA both eventually were). Update `cities`
list and `CITIES` dict at the top of `query_events.py` to add the new slug so
`--city nyc` validates, then update SKILL.md's frontmatter/intro and this
file's tables to mention the new city.

**Web search** — for anything not on the calendar (Luma-hosted side events,
official a16z sessions, speaker announcements): search
`"SF Tech Week 2026" <topic>` and `site:lu.ma "tech week" <topic>`. Treat what
you find as unverified until you've opened the page.

## Why not just curl it

`tech-week.com` is behind Vercel's bot protection: plain HTTP clients
(curl, requests, WebFetch) get a 429 "Security Checkpoint" page, not the
calendar. Everything above runs inside a real browser tab that has already
passed that check. `partiful.com` is friendlier — a normal GET returns the page
with the `__NEXT_DATA__` JSON embedded — but going through the browser keeps
one code path and also tells you the user's login/RSVP state.

If you have no browser tool at all: say so, hand the user the
`tech-week.com/calendar/sf` link with the keywords to search, and work from
the bundled data.

## Link durability

`techweek_url` values are signed redirects that tech-week.com regenerates on
every calendar fetch. Old ones have kept working, but if one 404s, refresh the
calendar or search the event by name to get a current link. `partiful_url`
values are stable.
