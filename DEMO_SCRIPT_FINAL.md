# AgentOS Command Center — Demo Script (< 10 minutes)
### Audience: Executive + Technical | Format: live demo at http://localhost:8000

> **Flow:** Problem → Use case → How AgentOS solves it → Why it beats alternatives → Live demo → Close.
> Browser zoom 110–125% so the room can read every number. Total target: **9:30**.

---

## ⏱️ TIME MAP

| # | Segment | Time |
|---|---------|------|
| 1 | The Problem | 0:00–1:00 |
| 2 | The Use Case | 1:00–1:45 |
| 3 | How AgentOS Solves It | 1:45–2:30 |
| 4 | Why AgentOS Beats the Alternatives | 2:30–3:30 |
| 5 | Live: Command Center | 3:30–4:45 |
| 6 | Live: Mailman (flagship) | 4:45–6:00 |
| 7 | Live: Wallstreet Wolf + AI-Times | 6:00–7:00 |
| 8 | Live: Hacker Digest + Extensibility | 7:00–7:45 |
| 9 | Live: Reliability internals | 7:45–8:45 |
| 10 | The Close + Ask | 8:45–9:30 |

---

## SEGMENT 1 — THE PROBLEM (0:00 – 1:00)
**Screen:** Dashboard, full screen (don't narrate it yet — set up the problem first).

> "Let me start with a problem every organization in this room is living with
> right now.
>
> Your most expensive people — your knowledge workers — spend **two to three
> hours every single day** on work a machine should do: triaging email,
> scanning markets, tracking industry news, copy-pasting between tools.
>
> The obvious fix is AI. But the AI tools that could automate this come with
> three deal-breakers. **One — they send your data to the cloud:** your
> emails, your financials, your internal documents leave your network and land
> on OpenAI's or Google's servers. **Two — they bill you forever:** per seat,
> per token, every month, with a cost that grows as you scale. **Three — you
> don't control them:** the vendor can change the model, raise the price, or
> read your data, and you have no say."

---

## SEGMENT 2 — THE USE CASE (1:00 – 1:45)
**Screen:** Dashboard still up.

> "So here's the use case we set out to solve. Imagine a team — sales, finance,
> operations, doesn't matter — drowning in inbound information. Hundreds of
> emails a day. Markets moving while they're in meetings. Industry news they
> never have time to read.
>
> What they actually need is a **team of tireless digital employees** that
> work 24/7 in the background: one that triages every email and flags what's
> urgent, one that watches the markets and briefs them each morning, one that
> curates the news that matters. Always on. Never distracted. And critically —
> running somewhere the company fully controls."

---

## SEGMENT 3 — HOW AGENTOS SOLVES IT (1:45 – 2:30)
**Screen:** Gesture across the dashboard.

> "That's exactly what **AgentOS Command Center** is. Four autonomous AI
> agents, managed by a central orchestrator, running entirely on **your own
> hardware** with a **local large language model — Qwen3 on Ollama.**
>
> The agents read, analyze, decide, and act on their own schedule. The
> orchestrator monitors system health, prevents conflicts, and serves this
> live operations dashboard. Every piece of AI thinking happens locally —
> **nothing leaves the building, and there's no per-token bill.**"

**[Technical, one breath]**
> "Stack: Python FastAPI backend, SQLite for persistence, APScheduler for cron,
> a WebSocket for real-time updates, and Qwen3 8B as the local inference engine."

---

## SEGMENT 4 — WHY AGENTOS BEATS THE ALTERNATIVES (2:30 – 3:30)
**Screen:** Cost Optimization card (scroll to it).

> "Now — why this, over the alternatives you already know?
>
> **Versus cloud AI assistants** — Copilot, ChatGPT Enterprise, Gemini: those
> are powerful, but your data leaves your network and you pay per user forever.
> AgentOS keeps data on-premise and costs effectively zero per run. Look at
> this card — **Cloud Cost Avoided** — that's real money we did not spend
> because inference is local.
>
> **Versus no-code automation** — Zapier, Make, Power Automate: those move data
> between apps but have no real intelligence and still call paid cloud AI for
> anything smart. AgentOS has a reasoning LLM at its core, on your machine.
>
> **Versus building it yourself** on raw APIs: that's months of integration and
> a fresh cloud bill. AgentOS is a **ready platform** — the orchestration,
> scheduling, monitoring, and dashboard are already built. You just point
> agents at your data.
>
> In short: **private like on-prem, intelligent like a frontier model, and
> free to run.** No competitor gives you all three."

---

## SEGMENT 5 — LIVE: THE COMMAND CENTER (3:30 – 4:45)
**Screen:** Top of Dashboard.

> "Let me show you it running live. This is mission control."

**[Point at KPI cards]**
> "Four live KPIs up top — total agent runs, a 98% success rate, tokens
> processed, average response time — each with a trend versus yesterday."

**[Point at the ops chart + donuts]**
> "This operations chart is real telemetry — CPU, memory, disk sampled every
> five seconds and streamed over WebSocket. If a resource crosses 90%, an
> alarm fires with a corrective action. These donuts show model performance
> and system health — every subsystem reporting Operational."

**[Point at Top Performing Agents]**
> "And here's the agent fleet with live run counts and success rates. Four
> agents — let me show you what each does for the business."

---

## SEGMENT 6 — LIVE: MAILMAN, THE FLAGSHIP (4:45 – 6:00)
**Screen:** Click **Mailman** tab.

> "Mailman is the one that pays for the platform on day one. It's connected to
> a **real, live Gmail inbox** right now."

**[Point at KPI strip + category breakdown]**
> "Over a thousand emails classified, sorted into seven categories — Urgent,
> Action Required, Follow-Up, Newsletter, and more. Remember: two-plus hours a
> day lost to email triage, per employee. Mailman does it automatically, every
> fifteen minutes, on every inbox. Multiply that across your headcount — that's
> the ROI."

**[Technical]**
> "The pipeline: Gmail OAuth 2.0, pull unread mail, Qwen3 returns structured
> JSON — category, priority, summary — then we apply Gmail labels, star
> high-priority mail, and fire an instant alert for anything urgent or from a
> configurable VIP list. Every email read locally; nothing sent to the cloud."

---

## SEGMENT 7 — LIVE: WALLSTREET WOLF + AI-TIMES (6:00 – 7:00)
**Screen:** Click **Wallstreet** tab.

> "Wallstreet Wolf — the market desk. Twenty-five stocks plus gold, silver, and
> currency pairs from Yahoo Finance — and the local AI writes a daily
> three-sentence briefing." **[read the commentary card aloud]** "Top gainers,
> top losers, at a glance. Your team is briefed before they sit down."

**[Click AI-Times tab]**
> "AI-Times — the intelligence feed. Five news videos, five expert briefings
> from YouTube each morning, with an AI-written digest. Staying current with
> zero effort."

---

## SEGMENT 8 — LIVE: HACKER DIGEST + EXTENSIBILITY (7:00 – 7:45)
**Screen:** Click **Hacker Digest** tab.

> "Our fourth agent curates the top tech stories and the AI writes a one-line
> 'why this matters' for each — and the parameters are user-configurable, live,
> no code."

**[The strategic point]**
> "But the real message here is extensibility. We built this custom agent on
> the same framework, fast. AgentOS isn't four agents — it's a **factory** for
> agents. Any repetitive, information-heavy job your teams do, we can build an
> agent for it in days, not months."

---

## SEGMENT 9 — LIVE: RELIABILITY INTERNALS (7:45 – 8:45)
**Screen:** Click **Scheduler**, then **Logs**.

> "For the engineers in the room — what makes this production-grade."

**[Scheduler]**
> "Every agent on a cron schedule, editable live from the browser — no restart."

**[Logs]**
> "Full observability — every action logged and filterable."

**[Architecture, no screen change]**
> "Three guarantees: an **LLM semaphore** so only one model call runs at a time
> — concurrent agents queue instead of thrashing the CPU, which prevents
> deadlock. An **agent watchdog** that detects and recovers crashed agents
> without restarting the platform — no zombie processes. And **resource-aware
> scheduling** that skips agents under load rather than failing them. Built to
> run unattended, 24/7."

---

## SEGMENT 10 — THE CLOSE + ASK (8:45 – 9:30)
**Screen:** Back to Dashboard, Cost Optimization card visible.

> "So to bring it home. AgentOS gives you three things no single competitor
> does: **data sovereignty** — everything stays behind your firewall;
> **near-zero cost** — no per-seat, no per-token, the curve bends in your favor
> as you scale; and **full control** — no vendor can change your price, your
> model, or read your data.
>
> My ask is a **thirty-day pilot**: point Mailman at one team's inboxes and let
> Wallstreet Wolf brief our analysts. We'll come back with hours saved and
> cloud dollars avoided.
>
> The technology to give every employee an AI team used to require a
> million-dollar cloud bill and a compliance nightmare. AgentOS puts it on our
> own hardware, for free. The question isn't whether AI agents will run the
> back office — it's whether we own ours, or rent someone else's. I'd like us
> to own it. Thank you — happy to take questions."

---

## 🆚 COMPETITIVE ONE-LINERS (keep handy for Q&A)

| Alternative | Their limitation | AgentOS advantage |
|-------------|------------------|-------------------|
| ChatGPT Enterprise / Copilot / Gemini | Data leaves network; per-seat billing | On-prem inference; ~zero per-run cost |
| Zapier / Make / Power Automate | No real reasoning; calls paid cloud AI | Local reasoning LLM at the core |
| DIY on raw APIs | Months of build + cloud bill | Ready platform: orchestration, scheduling, dashboard built-in |
| Self-hosted LLM only (no platform) | Just a model, no agents/ops | Full multi-agent fleet + monitoring + scheduling |

## ✅ PRE-DEMO CHECKLIST
- [ ] `ollama ps` shows qwen3 loaded
- [ ] Dashboard hard-refreshed (Ctrl+Shift+R); Cost card shows a non-zero figure
- [ ] Mailman, Wallstreet, AI-Times, Hacker Digest tabs all populated
- [ ] Trigger one agent right before recording so Live Activity has events
- [ ] Know your headcount × hourly cost for the Mailman ROI line

## 💬 ANTICIPATED Q&A
**"Run cost?"** → "Model downloaded once; runs cost ~nothing — no per-seat, no per-token."
**"Data safety?"** → "Fully local. No email or financial data leaves our network."
**"Accuracy?"** → "You watched it triage 1,200+ real emails and write a market brief. 98% run success, live."
**"Deploy time?"** → "Running today; a one-team pilot can start this week."
**"New agent for X?"** → "Subclass the base agent, register it, add a schedule — days, not months."
**"Scale beyond one box?"** → "Same architecture; add Ollama nodes behind the semaphore/queue."
