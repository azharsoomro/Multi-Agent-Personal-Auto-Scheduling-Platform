# Multi-Agent Auto-Scheduling Platform — 10-Minute Demo Script

**Target:** exactly 10 min | **Format:** screen recording + voiceover | **URL:** http://localhost:8000  
**Resolution:** 1920×1080, browser fullscreen, font size bumped to 125% for readability

---

## PRE-RECORDING CHECKLIST (do before hitting Record)

```
[ ] ollama ps               → qwen3:latest showing
[ ] Server running:
      cd backend
      ..\.venv\Scripts\python.exe main.py
[ ] http://localhost:8000 open in browser — Dashboard tab visible
[ ] Gmail inbox open in a second browser tab (to show received emails)
[ ] Trigger Wallstreet Wolf + Hacker Digest once so dashboard has live data
```

---

## SEGMENT 1 — Hook & Architecture (0:00 – 1:15)

**Screen:** Dashboard tab open at http://localhost:8000

> "What if your laptop could run four autonomous AI agents 24 hours a day —
> reading your inbox, tracking 25 stocks, curating Hacker News, and
> pulling fresh AI videos from YouTube — all powered by a completely
> local LLM, with zero cloud calls and zero ongoing cost?
>
> That is exactly what this platform does. I'm going to walk you through
> every layer of it in the next ten minutes."

**[Pause 2 seconds — let the dashboard settle on screen]**

> "The stack is: **Python 3.13 + FastAPI** for the backend, **SQLite** in
> WAL mode for storage, **plain HTML and JavaScript** for the dashboard —
> no React, no build step — and **Qwen3 running locally through Ollama**
> for all AI inference. Every email classified, every stock commentary
> written, every story curated — Qwen3 on your own CPU."

---

## SEGMENT 2 — Orchestrator & Live Dashboard (1:15 – 2:45)

**Screen:** Stay on Dashboard tab

> "Let's start with the **Main Orchestrator** — the brain of the whole system."

**[Point at the five metric cards across the top]**

> "The Orchestrator broadcasts five live metrics every **five seconds** via
> WebSocket — no polling, no refresh. Right now you can see CPU at about
> [X]%, RAM at [Y]%, Disk at [Z]%, active thread count, and total LLM
> calls with average latency.
>
> If any resource crosses **90%**, a red alarm banner appears at the top
> of the screen with a specific corrective action — for example, if RAM
> spikes it tells you to close other applications or reduce the LLM
> batch size. I'll show that in a moment."

**[Point at the progress bars — note colour change if any are high]**

> "The bars turn orange at 75% and red at 90%. The Orchestrator has a
> soft threshold at **85%** — if CPU or RAM is above that when an agent's
> cron fires, the agent is automatically skipped and logged as 'skipped'
> rather than failing. This prevents the system from choking when Qwen3
> is already under load."

**[Point at Agent Status panel]**

> "Left panel: all four agents with live status dots. Green means the
> last run succeeded. Each has a **Run** button to trigger manually
> right here from the dashboard."

**[Point at Live Events panel]**

> "Right panel: the live WebSocket event feed. Every agent start,
> finish, error, or crash appears here in real time."

**[Point at resource history chart at bottom]**

> "Bottom: a canvas chart of the last 60 readings — five seconds apart,
> so five minutes of history. Purple is CPU, cyan is RAM, orange is
> Disk. The dashed red line at 90% is the alarm threshold. You can
> literally watch CPU spike when Qwen3 starts generating tokens."

**[Point at the thread count metric card]**

> "Thread count tells us the Orchestrator is also running a **watchdog
> thread** that wakes every ten seconds. If an agent thread crashes
> unexpectedly — say, a network timeout kills it mid-run — the watchdog
> detects the dead thread, marks the DB record as 'crashed', and
> broadcasts a crash event to the dashboard. No need to restart the
> whole platform."

---

## SEGMENT 3 — Agents Tab & Scheduler (2:45 – 3:30)

**Screen:** Click **Agents** in sidebar

> "The Agents tab shows a detailed card for each agent — last run
> timestamp, duration, last message, and current status badge."

**[Point at any agent card]**

> "Two buttons: **Run Now** checks resources first before launching,
> **Force** bypasses the resource check and runs regardless — useful
> for demos."

**Screen:** Click **Scheduler** in sidebar

> "The Scheduler tab shows the four cron jobs and their next fire times.
> I can edit the schedule live — let me change AI-Times to run every
> two minutes for the demo."

**[Type `*/2 * * * *` into the AI-Times cron input and click Save]**

> "Saved. APScheduler will fire it within two minutes — we'll see it
> hit the Live Events feed without restarting anything."

---

## SEGMENT 4 — Agent-1: AI-Times (3:30 – 4:45)

**Screen:** Click **AI-Times** in sidebar

> "Agent-1 is **AI-Times** — a daily YouTube digest."

**[Point at the two-column layout]**

> "The tab is split into two sections. On the left: **five AI news
> videos** — stories from publications and research outlets published in
> the last 24 to 48 hours. On the right: **five creator highlights** —
> videos from educators like Andrej Karpathy, Yannic Kilcher, Two Minute
> Papers, and similar channels."

**[Point at a video card — thumbnail, title, channel chip, date chip]**

> "Each card shows the thumbnail, clickable title, channel name, and
> publish date. This is the exact output from the YouTube Data API v3
> — or, if no API key is configured, a curated mock list that keeps
> the full pipeline working for demo purposes."

**[Click the Refresh button]**

> "The Refresh button pulls the latest data from the database without
> re-running the agent. The Run Agent Now button triggers a full fetch,
> LLM call, and email send."

> "The **LLM step**: after fetching the videos, Qwen3 writes a
> two-sentence introduction for the email — something like 'Today's AI
> landscape is buzzing with breakthroughs...' That intro is at the top
> of the HTML digest email that lands in your inbox every morning at
> 08:00."

**[Switch to Gmail tab briefly — show the AI-Times email if present]**

> "Here's what the email looks like — the LLM-written intro, then two
> sections: News first, Creator picks below. Generated entirely locally."

**[Switch back to AI-Times tab]**

---

## SEGMENT 5 — Agent-2: Mailman (4:45 – 5:55)

**Screen:** Click **Mailman** in sidebar

> "Agent-2 is **Mailman** — an autonomous Gmail classifier."

**[Point at the category breakdown panel on the left]**

> "The left panel shows a category breakdown. Qwen3 classifies every
> email into one of seven categories: **Urgent, Action Required,
> Follow-Up, Newsletter, Notification, Personal, or Other**. The bars
> show the distribution across everything processed so far."

**[Point at the email list panel on the right]**

> "The right panel lists classified emails with their LLM-generated
> one-sentence summary, the category badge colour-coded by type, and
> how long ago it was processed."

**[Point at the key-people config input in the toolbar]**

> "Up here I can enter a comma-separated list of email addresses or
> domains to watch — my boss, a key client, my CTO. When Mailman
> finds an email from anyone on this list, it sends an **immediate
> priority alert** email regardless of category."

**[Type an example email and click Save]**

> "Saved live — no restart needed."

> "Under the hood: Mailman connects to Gmail via **OAuth 2.0**, scans
> up to 20 unread messages, and sends each one to Qwen3 with this
> prompt: *'Classify this email. Output JSON with keys: category,
> priority — high, medium, or low — and summary in one sentence.'*
> It then applies a Gmail label like AI/Urgent or AI/Newsletter,
> stars high-priority messages, and if anything is urgent or from
> the key-people list it fires an HTML alert email immediately."

**[Click Scan Inbox Now button]**

> "I can trigger a manual scan right here. Without Gmail OAuth
> credentials configured, it runs in demo mode classifying three
> representative mock emails — so the LLM reasoning and labelling
> logic are identical."

---

## SEGMENT 6 — Agent-3: Wallstreet Wolf (5:55 – 7:20)

**Screen:** Click **Wallstreet** in sidebar

> "Agent-3 is **Wallstreet Wolf** — our market intelligence agent."

**[Point at the green commentary card at top]**

> "The first thing you see is the **AI Market Commentary** — a three-
> sentence briefing written by Qwen3. Right now it says:
> *'[read the actual commentary text on screen].'*
> That was written locally, no Bloomberg terminal required."

**[Point at the Top 5 Gainers panel]**

> "Below that: **Block 1 — Top 5 Gainers.** Today that's [read top
> ticker] up [X]%, [second ticker] up [Y]%."

**[Point at the Top 5 Losers panel]**

> "**Block 2 — Top 5 Losers.** [Read them]. These are live prices
> from **Yahoo Finance** via the yfinance library — or realistic mock
> prices with random noise when markets are closed."

**[Point at the Metals & FX panel]**

> "**Block 3 right here** — Precious Metals and Currency Exchange.
> Gold at $[price], Silver at $[price]. And five FX pairs:
> EUR/USD, GBP/USD, USD/JPY, USD/CAD, AUD/USD. All updated every
> time the agent runs."

**[Scroll down to the Full Watchlist table]**

> "Below that: the **full watchlist** — all 25 tickers with price,
> percentage change colour-coded green or red, and market cap."

> "The agent fires at **16:30 UTC on weekdays** — right after the US
> market closes — and emails a complete HTML report."

**[Switch to Gmail briefly to show the Wallstreet email]**

> "Here's the email: commentary at the top, then gainers, losers,
> metals, FX, and the full 25-stock table. All built locally."

---

## SEGMENT 7 — Agent-4: Hacker Digest (7:20 – 8:30)

**Screen:** Click **Hacker Digest** in sidebar

> "Agent-4 is our custom agent — **Hacker Digest** — and it solves
> a real problem I face every day: Hacker News has hundreds of stories
> competing for attention. Who has 20 minutes to scroll HN every
> morning?"

**[Point at the story cards]**

> "The agent fetches the top stories from the **Hacker News Firebase
> API** — completely free, no key needed. Then Qwen3 reads each title
> and writes a single sentence: *why this story matters to a software
> engineer.* You can see the takeaways right here in the gold
> highlighted sections."

**[Read one takeaway aloud]**

> "That was written by Qwen3 running on this machine."

**[Point at score and comment chips]**

> "Each card shows the HN score, comment count, author, a link to
> the article, and a direct link to the HN discussion thread."

**[Point at the config inputs in the toolbar]**

> "The two inputs here are **user-configurable parameters** — how many
> stories to fetch from HN, and how many to curate and include in the
> email. Right now it fetches 30, curates the top 10. I can change
> that live."

**[Change curate to 5 and click Save]**

> "Next time the agent runs it will only curate five stories — useful
> if you want a shorter digest. The change takes effect immediately,
> no restart."

**[Click Run Agent Now]**

> "I'm triggering it live. The LLM calls are fast now — about 10
> seconds each with Qwen3's thinking mode disabled. We'll see it hit
> the Live Events feed on the Dashboard."

**[Switch to Dashboard briefly to show the event appearing in the live feed]**

> "There it is — agent started. It'll finish in about two minutes and
> the email will land in Gmail."

---

## SEGMENT 8 — Logs & Wrap-Up (8:30 – 10:00)

**Screen:** Click **Logs** in sidebar

> "Every action in the system is logged here — agent starts, LLM call
> completions, email sends, resource warnings, cron fires."

**[Click the dropdown and select hacker_digest]**

> "Filter to Hacker Digest — you can see the exact sequence: agent
> started, fetched 30 stories, agent finished in 86 seconds, success."

**[Switch back to dropdown — select orchestrator]**

> "The Orchestrator's own log shows the scheduler firing, resource
> checks passing or failing, and watchdog events if any agent thread
> ever crashes."

**Screen:** Click **Dashboard** to return to the live view

> "Let me leave you with the full picture running live."

**[Point at the dashboard — metrics updating in real time, live feed active]**

> "Five-second metric updates. Four agents. One LLM semaphore so
> Qwen3 never gets two requests at the same time. A watchdog that
> auto-recovers crashed threads. A scheduler you can modify live
> from the browser. Four email digests landing in your inbox on their
> own cron schedules. All of this — on your own machine, with a
> model you downloaded once."

> "The entire codebase is on GitHub — link in the description.
> Three commands to run it from scratch:
> `ollama pull qwen3:latest`,
> `pip install -r requirements.txt`,
> `python backend/main.py`.
> That's it."

**[Final wide shot of the dashboard with metrics, agent cards, and live feed all visible]**

> "This is what agentic AI looks like when you own the full stack."

**[End recording]**

---

## TIMING REFERENCE

| Time | Screen | What to show |
|------|--------|-------------|
| 0:00 – 1:15 | Dashboard | Hook + tech stack intro |
| 1:15 – 2:45 | Dashboard | Metrics, alarm, semaphore, watchdog, live feed, chart |
| 2:45 – 3:30 | Agents + Scheduler | Agent cards, Force button, live cron edit |
| 3:30 – 4:45 | AI-Times tab + Gmail | Two video sections, thumbnails, Refresh, email |
| 4:45 – 5:55 | Mailman tab | Category bars, email list, key-people config, scan trigger |
| 5:55 – 7:20 | Wallstreet tab + Gmail | Commentary, 3 blocks, metals, FX, full watchlist, email |
| 7:20 – 8:30 | Hacker Digest tab | Story cards, takeaways, config params, live trigger |
| 8:30 – 10:00 | Logs + Dashboard | Log filter, orchestrator log, final live shot |

---

## NUMBERS TO HAVE READY (glance before recording)

Run this in terminal right before you hit Record:

```powershell
Invoke-RestMethod "http://localhost:8000/api/status" | ConvertTo-Json -Depth 2
```

Note down:
- Current CPU / RAM / Disk %
- LLM total calls + avg ms
- Each agent's last_status and last_msg
- Market commentary text (first sentence to read aloud)

---

## WHAT EACH GRADED SECTION MAPS TO

| Rubric Item | Where it appears in the demo |
|---|---|
| Orchestrator (15 pts) | Seg 2: metrics cards, 5s updates, alarm, semaphore, watchdog, live feed |
| AI-Times (15 pts) | Seg 4: two-column video tab, thumbnails, Refresh button, Gmail email |
| Mailman (15 pts) | Seg 5: category breakdown, email list + summaries, key-people, scan trigger |
| Wallstreet Wolf (15 pts) | Seg 6: commentary card, 3 blocks, metals, FX, full watchlist, Gmail email |
| Agent-4 Hacker Digest (15 pts) | Seg 7: ranked cards with takeaways, configurable params, live trigger |
| Code Quality & Creativity (10 pts) | Briefly mention: semaphore, WAL mode, watchdog, think:false speedup, demo mode |
| Demo Video (15 pts) | All segments together — under 10 min, all 5 agents live |

---

## IF SOMETHING GOES WRONG

| Problem | Fix |
|---|---|
| Dashboard shows "Reconnecting" | Server crashed — re-run `python backend/main.py` |
| Ollama not running | `ollama serve` in a new terminal |
| Agent shows "skipped" | Resources too high — click Force on the agent card |
| Stocks tab empty | Trigger Wallstreet Wolf with Force button |
| HN stories empty | Trigger Hacker Digest with Force button |
| LLM call taking too long | think:false is set — if still slow, check `ollama ps` |
