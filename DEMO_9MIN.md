# AgentOS Command Center — 9-Minute Demo Script
### Dual audience: Executives + Technical stakeholders

**Format:** Live product demo at http://localhost:8000 + narration
**Principle:** At each stop, give the **business value** in one breath, then the
**technical proof** in the next. Executives hear the "why it matters"; engineers
hear the "how it works." Keep moving — 9 minutes is tight.

> **Browser zoom 110–125%** so the room can read every number.

---

## ⏱️ TIME MAP (9:00 total)

| # | Segment | Time | Exec hook / Tech proof |
|---|---------|------|------------------------|
| 1 | Opening + Architecture | 0:00–1:15 | Vision / full stack |
| 2 | Command Center | 1:15–2:45 | Self-running ops / metrics, gauges, donuts |
| 3 | AI-Times | 2:45–3:30 | Stay informed / YouTube API + LLM |
| 4 | Mailman (flagship) | 3:30–5:00 | Hours saved / OAuth + live classification |
| 5 | Wallstreet Wolf | 5:00–6:00 | Faster decisions / yfinance + LLM commentary |
| 6 | Hacker Digest + extensibility | 6:00–6:45 | Build any agent / custom agent in hours |
| 7 | Orchestrator internals | 6:45–8:00 | Reliability / semaphore, watchdog, scheduler |
| 8 | The close: cost, security, ask | 8:00–9:00 | ROI + data sovereignty |

---

## SEGMENT 1 — OPENING + ARCHITECTURE (0:00 – 1:15)
**Screen:** Dashboard, full screen.

> "This is **AgentOS Command Center** — a multi-agent AI platform where four
> autonomous agents read, analyze, and act around the clock. The headline:
> **every bit of AI inference runs locally** — no cloud, no per-token bills,
> no data leaving the building."

**[Technical, fast]**
> "Under the hood: a **Python FastAPI** backend, a **central orchestrator**
> managing the agent lifecycle, **APScheduler** for cron, **SQLite** in WAL
> mode for persistence, a **WebSocket** pushing live state to this dashboard,
> and **Qwen3 8B running on Ollama** as the local inference engine. Plain
> HTML/JS frontend — no build step. The whole thing runs on one machine."

---

## SEGMENT 2 — THE COMMAND CENTER (1:15 – 2:45)
**Screen:** Dashboard — sweep top to bottom.

**[Exec]**
> "This is mission control. At the top, four live KPIs — total agent runs,
> a 98% success rate, tokens processed, average response time — each with a
> trend delta versus the prior day."

**[Technical — point at the ops chart]**
> "This 'AI Operations Overview' is real telemetry. The orchestrator samples
> CPU, memory, and disk **every five seconds** and streams it over WebSocket —
> no polling. If any resource crosses 90%, an alarm banner fires with a
> recommended corrective action, and the scheduler will skip new agent
> launches above an 85% threshold to protect the box."

**[Point at the donuts]**
> "AI Model Performance — our success-rate donut, live. System Health —
> uptime, with every subsystem reporting Operational: the LLM engine, the
> database, the scheduler, resources."

**[Point at the Cost Optimization card — slow down here]**
> "And this is the card executives care about. **Cloud Cost Avoided** — every
> LLM call this platform made, priced against a GPT-4-class cloud rate. That's
> real money we did **not** spend, because inference is local. The red bar is
> what the cloud would've charged; the green bar is our actual cost —
> effectively zero."

---

## SEGMENT 3 — AI-TIMES (2:45 – 3:30)
**Screen:** Click **AI-Times** tab.

**[Exec]**
> "Agent one — AI-Times, an intelligence analyst. Every morning it delivers
> five industry-news videos and five expert briefings as an email digest.
> Your leaders stay current without burning an hour searching."

**[Technical]**
> "It calls the **YouTube Data API v3**, filters to the last 24–48 hours,
> dedupes, then Qwen3 writes the digest intro. Results are cached in SQLite
> and rendered here with thumbnails — and there's a manual Refresh and Run."

---

## SEGMENT 4 — MAILMAN, THE FLAGSHIP (3:30 – 5:00)
**Screen:** Click **Mailman** tab — KPI strip + live category breakdown.

**[Exec — let the numbers land]**
> "Agent two — Mailman — and this is the one that pays for the platform.
> It's connected to a **real, live Gmail inbox** right now. Look at the KPI
> strip — over a thousand emails classified, sorted into seven categories.
> The average knowledge worker loses two-plus hours a day to email triage.
> Mailman does it automatically, every fifteen minutes, on every inbox."

**[Technical — point at the breakdown + list]**
> "The pipeline: authenticate via **Gmail OAuth 2.0**, pull unread messages,
> and for each one Qwen3 returns structured JSON — category, priority, a
> one-line summary. We then call the Gmail API to apply labels like
> 'AI/Urgent', star high-priority mail, and if anything urgent or from a
> configurable VIP list appears, it fires an instant alert email."

**[Point at the key-people field]**
> "Name your VIPs here — the CEO emails, you're alerted immediately. And it's
> all local: not one email body ever touched a third-party server."

---

## SEGMENT 5 — WALLSTREET WOLF (5:00 – 6:00)
**Screen:** Click **Wallstreet** tab.

**[Exec — read the live commentary]**
> "Agent three — Wallstreet Wolf, the market desk. Numbers don't drive
> decisions, insight does — so the local AI writes a daily three-sentence
> briefing." **[read the commentary card aloud]** "Top gainers, top losers,
> at a glance. Your team walks in already briefed."

**[Technical]**
> "Live data from **Yahoo Finance** via yfinance — 25 equities plus gold,
> silver, and five FX pairs. Top-5 gainers and losers are computed here, the
> full watchlist persists to SQLite, and Qwen3 generates the commentary from
> the day's biggest movers. Daily email on a weekday cron after market close."

---

## SEGMENT 6 — HACKER DIGEST + EXTENSIBILITY (6:00 – 6:45)
**Screen:** Click **Hacker Digest** tab.

**[Technical first]**
> "Agent four pulls the top stories from the **Hacker News API** and Qwen3
> writes a one-line 'why this matters' for each. The fetch and curation counts
> are user-configurable, live, no code."

**[Exec — the strategic point]**
> "But don't focus on what it does — focus on what it proves. We built this
> custom agent quickly on the same framework. AgentOS isn't four agents —
> it's a **factory** for agents. Any repetitive, information-heavy task your
> teams do, we can stand up an agent for it. The platform grows with you."

---

## SEGMENT 7 — ORCHESTRATOR INTERNALS (6:45 – 8:00)
**Screen:** Click **Scheduler** tab, then **Logs** tab.

**[Technical — the reliability story]**
> "Now the engineering that makes this production-grade. The **Scheduler** —
> every agent on a cron, editable live from the browser; APScheduler reschedules
> on the fly, no restart."

**[Switch to Logs]**
> "Full **observability** — every agent start, LLM call, email send, and
> resource warning is logged and filterable by agent."

**[Speak to the architecture — no screen change needed]**
> "Three reliability guarantees worth calling out. **One — an LLM semaphore:**
> only one Qwen3 call runs at a time, so concurrent agents queue instead of
> thrashing a CPU-bound model — that's our deadlock prevention. **Two — an
> agent watchdog:** a background thread detects any crashed agent, marks it,
> and recovers state without restarting the platform — no zombie processes.
> **Three — resource-aware scheduling:** agents are skipped, not failed, when
> the system is under load. This is built to run unattended, 24/7."

---

## SEGMENT 8 — THE CLOSE: COST, SECURITY, ASK (8:00 – 9:00)
**Screen:** Back to Dashboard — Cost Optimization card visible.

**[Exec — the three-point close]**
> "Let me leave you with why this is defensible.
>
> **Security** — every email, every financial figure, every document the AI
> touches stays on our infrastructure. For a regulated business, that's the
> difference between 'yes' and 'legal says no.'
>
> **Cost** — the cloud-AI model bills per user, per token, forever. Our cost
> per run is effectively zero. That curve only bends in our favor as we scale.
>
> **Control** — no vendor can raise our price, change our terms, or read our
> data. We own the entire stack."

**[The ask]**
> "What I'm asking for is a thirty-day pilot — point Mailman at one team's
> inboxes and let Wallstreet Wolf brief our analysts. We'll come back with
> hours saved and cloud dollars avoided. The technology to give every employee
> an AI team used to require a million-dollar cloud bill and a compliance
> nightmare. AgentOS puts it behind our own firewall, for free. The question
> isn't whether AI agents will run the back office — it's whether we own ours
> or rent someone else's. I'd like us to own it."

> "Thank you — happy to take questions."

---

## 🎯 DUAL-AUDIENCE CHEAT SHEET

| Feature | Exec one-liner | Tech one-liner |
|---------|----------------|----------------|
| Local Qwen3 | "Zero cloud cost, zero data leakage" | "Ollama, 8B model, on-prem inference" |
| Cost card | "Real money not spent" | "LLM calls × GPT-4 blended rate, durable estimate" |
| Mailman | "2 hrs/day back per employee" | "OAuth 2.0 + JSON classification + Gmail labels" |
| Wallstreet | "Team briefed before they sit down" | "yfinance + LLM commentary, daily cron" |
| Semaphore | "Never falls over" | "1-permit lock serializes LLM, prevents deadlock" |
| Watchdog | "Self-healing" | "Thread liveness check, state recovery, no zombies" |
| Extensibility | "A factory for agents" | "Subclass BaseAgent, register, add cron" |

## ✅ PRE-DEMO CHECKLIST
- [ ] `ollama ps` shows qwen3 loaded
- [ ] Server running; dashboard hard-refreshed (Ctrl+Shift+R)
- [ ] Mailman tab shows real classified emails + category breakdown
- [ ] Wallstreet tab shows commentary + gainers/losers + metals/FX
- [ ] Hacker Digest + AI-Times tabs populated
- [ ] Cost Optimization card shows a non-zero dollar figure
- [ ] Trigger one agent right before recording so Live Activity has events
- [ ] Know your headcount × hourly cost for the Mailman ROI line

## 💬 ANTICIPATED Q&A
**"Run cost?"** → "Model downloaded once; runs cost ~nothing — no per-seat, no per-token."
**"Data safety?"** → "Fully local. No email or financial data leaves our network."
**"Accuracy?"** → "You watched it triage 1,200+ real emails and write a market brief. 98% run success, live."
**"Deploy time?"** → "Running today; a one-team pilot can start this week."
**"New agent for X?"** → "Subclass the base agent, register it, add a schedule — days, not months."
**"Scale beyond one box?"** → "Same architecture; add Ollama nodes behind the semaphore/queue."
