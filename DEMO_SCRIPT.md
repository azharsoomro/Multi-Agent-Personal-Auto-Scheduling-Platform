# Multi-Agent Auto-Scheduling Platform — 10-Minute Demo Script

**Target duration:** 10 min  |  **Format:** Screen recording with voiceover  
**URL:** http://localhost:8000  |  **Recording tip:** 1920×1080, mic on, browser fullscreen

---

## PRE-RECORDING CHECKLIST
- [ ] Ollama running: `curl http://localhost:11434/api/tags`
- [ ] Server running: `cd backend && ../.venv/Scripts/python main.py`
- [ ] Dashboard open at http://localhost:8000
- [ ] Terminal visible in a split or second monitor
- [ ] Gmail inbox open in a second tab (to show received emails)

---

## SEGMENT 1 — Hook & Architecture Overview (0:00 – 1:30)

**Screen:** Architecture diagram (`architecture.svg`) opened in browser

> "What if you could have five AI agents running 24/7 on your laptop — 
> autonomously reading your emails, tracking the stock market, curating 
> tech news, and sending you polished daily briefings — all powered by a 
> completely local LLM, zero cloud, zero cost?"
>
> "That's exactly what we built. This is the Multi-Agent Auto-Scheduling 
> Platform. Let me walk you through every piece of it."

**Point at diagram while narrating:**

> "At the top we have the **Main Orchestrator** — the brain of the whole 
> system. It monitors CPU, RAM and disk in real time, manages a semaphore 
> queue so agents don't compete for the LLM simultaneously, and handles 
> the cron scheduler that fires each agent on its own schedule."
>
> "Below it are four specialized agents. **AI-Times** pulls the latest AI 
> videos from YouTube and emails you an HTML digest. **Mailman** watches 
> your Gmail inbox and classifies every email using the LLM — labeling, 
> starring, and alerting on urgent ones. **Wallstreet Wolf** tracks 25 
> tech stocks and sends a daily market report with AI commentary. And our 
> custom agent, **Hacker Digest**, fetches the top Hacker News stories 
> and uses the LLM to curate the 10 most relevant ones for a software 
> engineer — then emails a digest."
>
> "All AI inference runs locally through **Ollama with Qwen3** — a 5GB 
> model on your own machine. The backend is **Python 3.12 + FastAPI**, 
> storage is **SQLite**, and the dashboard uses plain HTML and JavaScript 
> with a WebSocket for real-time updates. No React, no build step, 
> nothing to install beyond Python."

---

## SEGMENT 2 — Dashboard Live Overview (1:30 – 3:00)

**Screen:** Switch to http://localhost:8000 → Dashboard tab

> "Here's the live dashboard. Let me take you through it."

**Point at metrics row:**

> "The top row shows real-time system metrics pulled every 30 seconds 
> by the Orchestrator. Right now CPU is around 25%, RAM is at 83% — 
> we're running Qwen3 on 34 GB of RAM so it eats memory — and disk 
> is at 70%. The Orchestrator has a configurable threshold: if RAM 
> hits 85%, it automatically pauses new agent launches to prevent 
> the system from choking. You can see that in action when we have 
> too many agents competing at once."
>
> "The fourth card shows LLM call statistics — how many total Qwen3 
> calls have been made and what the average latency is. Right now 
> we've made 20 calls with an average of about 60 seconds per call."

**Point at Agent Status panel:**

> "The left panel shows all four agents. Green dots mean the last run 
> succeeded. We can see AI-Times ran 46 seconds ago, Mailman just 
> finished classifying emails, Wallstreet Wolf tracked 25 stocks, 
> and Hacker Digest sent its digest. Every agent has a Run button 
> right here — I can trigger any of them manually."

**Point at Live Events panel:**

> "On the right is the live event feed. Every time an agent starts, 
> finishes, or errors, a message appears here in real time via 
> WebSocket. No page refresh needed."

**Point at resource chart:**

> "At the bottom, a canvas chart plots the last 30 resource readings 
> — purple is CPU, cyan is RAM, orange is disk. You can watch the 
> spikes when an LLM call is in flight."

---

## SEGMENT 3 — Agent 1: AI-Times Deep Dive (3:00 – 4:30)

**Screen:** Click Agents tab → AI-Times card

> "Let's go deep on each agent. **AI-Times** is our YouTube curator."

**Show the agent detail card:**

> "**Input:** It calls the YouTube Data API v3 with four search queries — 
> 'artificial intelligence 2025', 'large language models tutorial', 
> 'AI agents automation', and 'machine learning breakthrough'. It 
> fetches the top 5 results per query from the last 7 days, 
> deduplicates by video ID, and caps at 20 videos."
>
> "**LLM step:** It then sends a single prompt to Qwen3: 
> 'Write a 2-sentence enthusiastic introduction for a daily AI video 
> digest featuring N curated videos.' The model returns the copy that 
> appears at the top of the email."
>
> "**Output:** A polished HTML email with thumbnails, channel names, 
> publish dates, and the LLM-written intro — sent to your Gmail 
> via SMTP."
>
> "It runs on a **cron schedule at 08:00 UTC every day**. If you 
> haven't configured a YouTube API key, it runs in demo mode with 
> mock video data — so the pipeline, the LLM call, and the email 
> all still work end-to-end."

**Switch to Gmail tab — show the received AI-Times email:**

> "And here's the email that arrived in Gmail. Clean HTML layout, 
> the LLM-written intro at the top, each video card with a thumbnail, 
> channel tag, date tag, and description. This is generated entirely 
> locally — Qwen3 wrote this intro, the Python code built the HTML."

---

## SEGMENT 4 — Agent 2: Mailman Deep Dive (4:30 – 5:45)

**Screen:** Agents tab → Mailman card. Then switch to Logs tab, filter to mailman

> "**Mailman** is the Gmail classifier. Let me show you the logs."

**Point at log lines:**

> "You can see exactly what happened on the last run. It picked up 
> three emails from the inbox:"
>
> - `[DEMO] URGENT: Server Down in Production → work / HIGH`  
> - `[DEMO] Weekly Newsletter — AI Trends → newsletter / LOW`  
> - `[DEMO] Invoice #4521 Due → finance / HIGH`
>
> "**Input per email:** Subject, sender, and up to 500 characters of 
> body text — sent to Qwen3 as a JSON classification prompt."
>
> "**LLM prompt:**  
> 'Classify this email. Output JSON with keys: category 
> (urgent/newsletter/work/social/spam/finance/personal/other), 
> priority (high/medium/low), summary (one sentence max 20 words).'"
>
> "**LLM output:**  
> `{ category: 'work', priority: 'high', summary: 'Production database unreachable, all services impacted' }`"
>
> "**What it does with that output:** It applies a Gmail label — 
> AI/Work, AI/Newsletter, AI/Finance — and for high-priority emails, 
> it adds a star. If any high-priority emails are found, it fires 
> an urgent alert HTML email immediately."
>
> "It runs every **15 minutes**. In Gmail credentials demo mode it 
> classifies mock emails — but the LLM reasoning and label logic 
> are identical to what runs on your real inbox."

---

## SEGMENT 5 — Agent 3: Wallstreet Wolf Deep Dive (5:45 – 7:00)

**Screen:** Click Stocks tab — show the full stock table

> "**Wallstreet Wolf** tracks 25 tech stocks."

**Scroll through the stock table:**

> "**Input:** 25 tickers — AAPL, MSFT, GOOGL, NVDA, META, TSLA, 
> AMD, COIN, PLTR, ARM, ASML and 14 others — fetched via 
> **Yahoo Finance** using the yfinance library. Price, previous 
> close, volume, and market cap for each."
>
> "Today's session: **20 gainers, 5 losers.** The biggest movers 
> were COIN up 4%, NVDA up 3.5%, PLTR up 3.1%. On the losing side, 
> SMCI down 3.1%, TSLA down 2.9%, PYPL down 2.1%."
>
> "**LLM step:** The top 5 movers by absolute change are summarized 
> into a bullet list and sent to Qwen3 with this prompt: 
> 'You are a sharp Wall Street analyst. Given today's top movers, 
> write a punchy 3-sentence market commentary. Be specific, 
> insightful, no fluff.'"
>
> "Qwen3 produces something like: 
> 'Crypto names led the charge today with COIN surging 4% on volume, 
> while semis showed resilience with NVDA breaking higher on AI 
> infrastructure demand. TSLA continued its retreat amid margin 
> concerns, dragging EV sentiment lower. The divergence between 
> high-beta tech winners and legacy names like INTC and PYPL 
> suggests rotation toward growth is still in play.'"
>
> "**Output:** A formatted HTML market report email — the LLM 
> commentary, a full sortable table of all 25 tickers with 
> colour-coded up/down arrows, and a stats banner showing total 
> tracked, gainers, losers, and average change."
>
> "Scheduled to fire at **16:30 UTC on weekdays** — right after 
> the US market closes."

**Switch to Gmail — show the Wallstreet Wolf email:**

> "Here's the email. The commentary, the colour-coded table, 
> all generated locally."

---

## SEGMENT 6 — Agent 4: Hacker Digest Deep Dive (7:00 – 8:15)

**Screen:** Agents tab → Hacker Digest. Then show a Hacker Digest email

> "The fourth agent is our custom one — **Hacker Digest** — and 
> it solves a real problem: information overload from Hacker News."

> "**Input:** The Hacker News public Firebase API — completely free, 
> no key needed. It fetches the IDs of the top 30 stories, then 
> hits the item endpoint for each to get the title, URL, score, 
> comment count, and author."
>
> "**LLM step:** For each of the top 10 stories by score, it asks 
> Qwen3: 'In one sentence (max 15 words), why does this story matter 
> to a software engineer?' That's 10 sequential LLM calls — each 
> fast because the prompt is tiny."
>
> "It also generates an overview: 'In 2 sentences, summarize today's 
> tech conversation on Hacker News. Top stories include: [titles].'"
>
> "**Real output from today's run:**
> The digest included stories on open-source model releases, 
> AI agent frameworks, performance engineering, and a viral 
> debugging thread. Each story gets a one-line takeaway, the score, 
> comment count, a link to the article and a link to the HN thread."
>
> "**Output:** An HTML email with the AI overview at the top, 
> then 10 story cards ranked by score, the top 3 highlighted 
> in orange. Runs daily at **09:00 UTC**."

**Show the email:**

> "Here's what landed in Gmail. Clean, readable, the kind of digest 
> you'd actually want to receive every morning."

---

## SEGMENT 7 — Orchestrator & Scheduler Live Demo (8:15 – 9:15)

**Screen:** Click Scheduler tab

> "Now the Orchestrator — the piece that ties everything together."

**Show the jobs table:**

> "Every agent has a next-run time. I can change the schedule live — 
> let me reschedule Hacker Digest to run every minute for the demo."

**Type `* * * * *` and hit Save:**

> "Done. APScheduler will fire it in under 60 seconds."

**Switch to Dashboard tab — watch Live Events:**

> "You can see the event appear in the live feed when it fires. 
> The Orchestrator checks resources first — if CPU or RAM is above 
> threshold, the agent is automatically skipped and logged as 
> 'skipped' rather than failing. This is the resource-aware 
> scheduling in action."

**Switch to Logs tab:**

> "Every single action is logged here — agent starts, LLM call 
> completions, email sends, resource constraint warnings, 
> scheduler fires. Filter by agent using the dropdown."

> "The LLM queue is a Python threading Semaphore set to 1 — only 
> one Qwen3 call runs at a time. If two agents fire simultaneously, 
> one waits in the queue for up to 10 minutes. This prevents 
> CPU/memory contention and deadlock. We saw this in practice — 
> when all 4 agents triggered at once, the Orchestrator correctly 
> serialized them through the queue."

---

## SEGMENT 8 — Wrap-Up & GitHub (9:15 – 10:00)

**Screen:** Show the GitHub repo page (or terminal with `git log --oneline`)

> "Everything you saw today is in the public GitHub repo — 
> link in the description. The README has complete setup 
> instructions, including how to get your Gmail App Password, 
> YouTube API key, and Gmail OAuth credentials."

**Quick scroll through the repo file tree:**

> "The backend is 13 Python files — orchestrator, scheduler, 
> LLM client, database models, email utils, and one file per agent. 
> The frontend is three files — HTML, CSS, JavaScript. No framework, 
> no build toolchain. Clone it, create a .env from the example, 
> run `python main.py`, open localhost 8000."

**Back to Dashboard — final shot:**

> "Five agents. One orchestrator. Entirely local AI inference. 
> A real-time dashboard. Email digests landing in your inbox. 
> All running on your own machine."
>
> "This is what agentic AI looks like when you own the whole stack."

---

## SCREEN RECORDING FLOW SUMMARY

| Time | Tab / Screen | Key action |
|------|-------------|------------|
| 0:00–1:30 | `architecture.svg` in browser | Narrate diagram top-to-bottom |
| 1:30–3:00 | Dashboard tab | Point at metrics, agent cards, live feed, chart |
| 3:00–4:30 | Agents tab → AI-Times card + Gmail email | Show input/output |
| 4:30–5:45 | Logs tab (filter: mailman) | Read classification log lines |
| 5:45–7:00 | Stocks tab + Gmail email | Scroll stock table, read LLM commentary |
| 7:00–8:15 | Agents tab → Hacker Digest + Gmail email | Show story cards + overview |
| 8:15–9:15 | Scheduler tab → Dashboard live feed → Logs tab | Reschedule, watch fire |
| 9:15–10:00 | GitHub repo + Dashboard | Wrap-up shot |

---

## TALKING-POINT CHEATSHEET (if you lose your place)

**AI-Times:**  
Input = YouTube search queries → 20 videos  
LLM = 1 call for intro paragraph  
Output = HTML email digest  

**Mailman:**  
Input = unread Gmail messages (up to 20)  
LLM = 1 call per email → JSON: category + priority + summary  
Output = Gmail labels + stars + urgent alert email  

**Wallstreet Wolf:**  
Input = 25 tickers via Yahoo Finance → price, change%, volume, market cap  
LLM = 1 call → 3-sentence market commentary on top movers  
Output = HTML market report email with full stock table  

**Hacker Digest:**  
Input = HN Firebase API → top 30 stories (free, no key)  
LLM = 11 calls (1 overview + 1 per story takeaway)  
Output = HTML digest email with 10 curated stories  

**Orchestrator:**  
Monitors CPU/RAM/Disk every 30 seconds  
Semaphore = 1 LLM slot, 10-min queue timeout  
Threshold = pauses agents at 85% CPU or RAM  
APScheduler = cron-based firing, live-updateable via REST API  
WebSocket = broadcasts all events to dashboard in real time  

---

## COMMON QUESTIONS TO ANTICIPATE

**Q: Why Qwen3 specifically?**  
A: Strong instruction-following, fits in 5 GB (Q4 quantized), excellent JSON output, runs CPU-only on 16 GB+ RAM.

**Q: Why not just use GPT-4?**  
A: Zero cost, complete privacy — emails and stock data never leave the machine. Also demonstrates local AI is production-capable.

**Q: What's the LLM latency?**  
A: 30–90 seconds per call on CPU. With a GPU it'd be 2–5 seconds. The semaphore queue serializes calls so agents don't compete.

**Q: Can it run 24/7?**  
A: Yes — just keep `python main.py` running. The Scheduler picks up missed jobs on restart if within the misfire grace window (60 seconds).

**Q: How do you extend it with a 6th agent?**  
A: Subclass `BaseAgent`, implement `_execute()`, add it to `AGENTS` dict in `orchestrator.py`, add a cron entry to `.env`.
