# ⚡ Multi-Agent Auto-Scheduling Platform

A fully local multi-agent system orchestrated by a central manager, running on **Ollama + Qwen3**. Five specialized agents handle real tasks autonomously on a cron schedule, with a live web dashboard.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Main Orchestrator                             │
│  • Resource monitor (CPU/RAM/Disk)   • LLM semaphore queue      │
│  • Agent lifecycle management        • Deadlock prevention       │
│  • WebSocket broadcast               • APScheduler integration   │
└──────────┬──────────────────────────────────────────────────────┘
           │  spawns & monitors
    ┌──────┴──────┬──────────────┬──────────────┬────────────────┐
    ▼             ▼              ▼               ▼                ▼
┌────────┐  ┌─────────┐  ┌──────────────┐  ┌──────────┐  ┌──────────────┐
│AI-Times│  │ Mailman │  │Wallstreet    │  │ Hacker   │  │  Orchestrator│
│        │  │         │  │Wolf          │  │ Digest   │  │  (self)      │
│YouTube │  │ Gmail   │  │Yahoo Finance │  │ HN API   │  │              │
│→ email │  │ OAuth   │  │→ 25 stocks   │  │→ email   │  │              │
│digest  │  │ LLM     │  │→ LLM comment │  │ digest   │  │              │
│        │  │ labels  │  │→ email       │  │          │  │              │
└────────┘  └─────────┘  └──────────────┘  └──────────┘  └──────────────┘
                                │
                         ┌──────┴──────┐
                         │   Ollama    │
                         │  Qwen3:LLM  │
                         └─────────────┘
```

**Storage:** SQLite (`data/platform.db`) — agent runs, logs, stock snapshots, email records, system metrics  
**Frontend:** Plain HTML/CSS/JS — WebSocket real-time updates, no build step  
**Backend:** FastAPI + APScheduler + SQLAlchemy

---

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.12+
- [Ollama](https://ollama.com/) installed and running
- Qwen3 model pulled

```bash
# Install Ollama (Windows — download from ollama.com)
# Then pull the model:
ollama pull qwen3:latest
```

### 2. Clone & Install

```bash
git clone https://github.com/YOUR_USERNAME/multi-agent-platform.git
cd multi-agent-platform

python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Configure

```bash
cp .env.example .env
# Edit .env with your settings (see Configuration section below)
```

### 4. Run

```bash
cd backend
python main.py
```

Open **http://localhost:8000** in your browser.

---

## ⚙️ Configuration

Edit `.env` in the project root:

| Variable | Description | Required |
|---|---|---|
| `OLLAMA_MODEL` | Ollama model name (e.g. `qwen3:latest`) | Yes |
| `EMAIL_ADDRESS` | Gmail address for sending emails | For email |
| `EMAIL_PASSWORD` | Gmail App Password (not your login password) | For email |
| `YOUTUBE_API_KEY` | YouTube Data API v3 key | For AI-Times |
| `GMAIL_CREDENTIALS_FILE` | Path to Gmail OAuth credentials JSON | For Mailman |
| `STOCK_TICKERS` | Comma-separated list of ticker symbols | Optional |

### Gmail App Password Setup
1. Enable 2-Factor Authentication on your Google account
2. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
3. Create an App Password for "Mail"
4. Paste the 16-character password as `EMAIL_PASSWORD` in `.env`

### YouTube API Key Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project → Enable **YouTube Data API v3**
3. Create API Key → copy it as `YOUTUBE_API_KEY`
4. Leave blank to run in demo mode (mock videos)

### Gmail OAuth (Mailman)
1. In Google Cloud Console → OAuth 2.0 → Desktop App credentials
2. Download as `gmail_credentials.json` in the project root
3. First run will open a browser for OAuth consent
4. Leave blank to run Mailman in demo mode (classifies mock emails)

---

## 🤖 Agents

### 1. AI-Times (`ai_times`)
- Searches YouTube for top AI/ML videos from the past 7 days
- LLM writes an intro paragraph
- Sends a polished HTML email digest
- **Schedule:** Daily at 08:00 UTC
- **Fallback:** Works in demo mode without a YouTube API key

### 2. Mailman (`mailman`)
- Fetches unread Gmail messages (up to 20 per run)
- Classifies each with Qwen3: category + priority + 1-sentence summary
- Auto-labels (`AI/Work`, `AI/Urgent`, etc.) and stars high-priority emails
- Sends an alert email when high-priority emails are detected
- **Schedule:** Every 15 minutes
- **Fallback:** Demo mode with mock emails if no Gmail credentials

### 3. Wallstreet Wolf (`wallstreet_wolf`)
- Tracks 25 stocks via Yahoo Finance (no API key needed)
- Qwen3 generates a punchy 3-sentence market commentary on the top movers
- Sends a formatted HTML market report email
- **Schedule:** Weekdays at 16:30 UTC (after US market close)

### 4. Hacker Digest (`hacker_digest`)
- Fetches top 30 stories from Hacker News public API (no key needed)
- Qwen3 curates the 10 most interesting for a software engineer + adds takeaways
- Sends a styled HTML digest email
- **Schedule:** Daily at 09:00 UTC

### 5. Orchestrator (Central Manager)
- Monitors CPU, RAM, Disk every 30 seconds
- Enforces resource thresholds — pauses agent launches if system is stressed
- Semaphore-based LLM queue (max 2 concurrent calls, deadlock prevention)
- Broadcasts all events to the dashboard via WebSocket

---

## 📊 Dashboard

Access at **http://localhost:8000**

| Tab | Description |
|---|---|
| Dashboard | Live CPU/RAM/Disk gauges, agent status cards, real-time event feed, resource chart |
| Agents | Detailed cards for each agent — run now, force run, last result |
| Scheduler | Next run times, update cron expressions live |
| Stocks | Latest stock snapshots, sorted by % change |
| Emails | Full history of sent emails per agent |
| Logs | Searchable log stream, filterable by agent |

---

## 🛠️ API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/status` | Full orchestrator + agent status |
| `POST` | `/api/agents/{name}/trigger` | Trigger agent manually |
| `GET` | `/api/scheduler/jobs` | List scheduled jobs + next runs |
| `PUT` | `/api/scheduler/{name}` | Update agent cron schedule |
| `GET` | `/api/stocks` | Latest stock snapshots |
| `GET` | `/api/emails` | Email send history |
| `GET` | `/api/logs` | Agent logs (filterable) |
| `GET` | `/api/metrics/history` | Historical CPU/RAM/Disk |
| `WS` | `/ws` | Real-time event stream |

---

## 📁 Project Structure

```
multi-agent-platform/
├── backend/
│   ├── main.py              # FastAPI app + WebSocket
│   ├── orchestrator.py      # Central orchestrator
│   ├── scheduler.py         # APScheduler cron integration
│   ├── database.py          # SQLAlchemy models + SQLite
│   ├── llm_client.py        # Ollama client with semaphore queue
│   ├── email_utils.py       # SMTP email helper
│   ├── config.py            # All configuration
│   └── agents/
│       ├── base_agent.py    # Abstract base — run lifecycle
│       ├── ai_times.py      # YouTube → email digest
│       ├── mailman.py       # Gmail classifier
│       ├── wallstreet_wolf.py  # Stock tracker
│       └── hacker_digest.py # HN story curator
├── frontend/
│   ├── index.html           # Dashboard SPA
│   ├── style.css            # Dark theme
│   └── app.js               # WebSocket + REST client
├── data/                    # SQLite DB + Gmail token (gitignored)
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🔒 Security Notes

- Never commit `.env` — it contains your email password and API keys
- `data/` is gitignored — contains the database and Gmail OAuth token
- Gmail OAuth token is stored locally only (`data/gmail_token.json`)
- Ollama runs entirely on your machine — no data leaves your system

---

## 📋 Requirements Met

- ✅ All AI inference is LOCAL (Ollama + Qwen3)
- ✅ Python 3.12 backend (FastAPI)
- ✅ Plain HTML/JS frontend (no build step)
- ✅ SQLite storage
- ✅ 5 agents: Orchestrator, AI-Times, Mailman, Wallstreet Wolf, Hacker Digest
- ✅ Resource monitoring with thresholds
- ✅ LLM scheduling with deadlock prevention (semaphore)
- ✅ Cron-based scheduling (APScheduler)
- ✅ Web dashboard with real-time WebSocket updates
- ✅ Email digests (HTML)
- ✅ Demo modes for agents that need external credentials
