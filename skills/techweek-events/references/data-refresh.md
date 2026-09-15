# When the bundled data isn't enough, and how to go to the web

## What's in the dataset (and what isn't)

`assets/events.json` — every event on the tech-week.com SF calendar as of the
`scraped_at` date in `assets/dataset.json` (run `query_events.py stats`).

| you have, for all ~1,640 events | you have only for ~440 "priority" events | you don't have |
|---|---|---|
| name, host, co-hosts, sponsors | full description (~900 chars) | events added after `scraped_at` |
| day, start time, neighborhood | end time, exact venue neighborhood | events that were removed or rescheduled since |
| track tags, featured flag | RSVP type (RSVP vs APPLY), capacity, at-capacity | live capacity / waitlist state |
| registration status (as of scrape) | Partiful URL | descriptions for the other ~1,200 |
| tech-week.com redirect link | | NYC / LA Tech Week |
| | | which events sell tickets (Partiful hides pricing from the calendar; `partiful_extract.js` reports `ticketed`) |

The ~440 detailed events are the featured and track-tagged ones — that's where
the substantive programming is. The remaining ~1,200 are dominated by run
clubs, coffee meetups, and small mixers; they're searchable by name and host
but you'd have to open one to know more.

## When to go live

- The user asks about **a specific event** you can't find by name or host →
  it's new or renamed. Check the calendar.
- The user is asking **during Tech Week** (Oct 5–11) or within a few days
  before it → registration states and capacities have moved. Refresh, or at
  least open the specific events you're about to recommend.
- `scraped_at` is **more than ~5 days old** and the user wants a plan → refresh.
- A goal has **no strong matches** → the answer may be in an event without a
  description. Open the top few candidates from `search` and read them.
- The user asks about **NYC or LA** → not bundled. Same scripts work; change
  the calendar URL.
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
`https://www.tech-week.com/calendar/sf`, run:

```js
await (await fetch('/api/trpc/calendar.events?batch=1', {method:'POST',
  headers:{'content-type':'application/json'},
  body: JSON.stringify({"0":{city:"sf",q:"<keywords>",featured:false,track:[],sponsor:[],theme:[],
    format:[],location:[],time:[],host:[],sortBy:"time",sortOrder:"asc",cursor:1,direction:"forward"}})
})).json()
```

`[0].result.data.results` is a page of 48 events (`total` tells you how many
match). Filter by `track: ["fintech"]`, or by `day` if the site exposes it
(check the request the page itself makes when you click a day tab).

**Full refresh** — from a tab on the calendar, execute
`scripts/refresh_calendar.js` (strip comment lines if your tool has a payload
limit). It pulls every page plus the nine track queries (~15–40s) into
`window.__twRefresh` and returns a summary. Pull the events out in slices of
~400 (`JSON.stringify(window.__twRefresh.events.slice(0,400))`, then 400–800,
…), save each slice, concatenate into one JSON array, then:

```
python3 scripts/merge_refresh.py fresh.json          # preview: added / changed / removed
python3 scripts/merge_refresh.py fresh.json --write  # apply, and rebuild events-index.md
```

The merge keeps Partiful-sourced fields, updates calendar fields, adds new
events with `detail_status: "none"`, and marks vanished ones
`registration_status: "removed"`.

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
