"""Central configuration — all secrets loaded from .env"""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent.parent
load_dotenv(BASE_DIR / ".env")

# ── Ollama ────────────────────────────────────────────────────────────────────
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL", "qwen3:latest")

# ── Email (Gmail SMTP) ────────────────────────────────────────────────────────
SMTP_HOST     = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT     = int(os.getenv("SMTP_PORT", "587"))
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")        # App Password
EMAIL_RECIPIENT = os.getenv("EMAIL_RECIPIENT", EMAIL_ADDRESS)

# ── YouTube ───────────────────────────────────────────────────────────────────
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")

# ── Gmail OAuth (Mailman) ─────────────────────────────────────────────────────
def _resolve(path_str: str) -> str:
    """Resolve a configured path against the project root if it's relative."""
    p = Path(path_str)
    return str(p if p.is_absolute() else (BASE_DIR / p))

GMAIL_CREDENTIALS_FILE = _resolve(os.getenv("GMAIL_CREDENTIALS_FILE", "gmail_credentials.json"))
GMAIL_TOKEN_FILE       = _resolve(os.getenv("GMAIL_TOKEN_FILE", "data/gmail_token.json"))

# ── Database ──────────────────────────────────────────────────────────────────
DATABASE_URL = f"sqlite:///{BASE_DIR / 'data' / 'platform.db'}"

# ── Scheduler defaults ────────────────────────────────────────────────────────
AGENT_SCHEDULES = {
    "ai_times":         os.getenv("SCHEDULE_AI_TIMES",        "0 8 * * *"),   # 08:00 daily
    "mailman":          os.getenv("SCHEDULE_MAILMAN",          "*/15 * * * *"), # every 15 min
    "wallstreet_wolf":  os.getenv("SCHEDULE_WALLSTREET",       "30 16 * * 1-5"),# 16:30 weekdays
    "hacker_digest":    os.getenv("SCHEDULE_HACKER_DIGEST",    "0 9 * * *"),   # 09:00 daily
}

# ── Resource thresholds ───────────────────────────────────────────────────────
CPU_THRESHOLD_PCT  = float(os.getenv("CPU_THRESHOLD_PCT",  "85"))
RAM_THRESHOLD_PCT  = float(os.getenv("RAM_THRESHOLD_PCT",  "85"))
DISK_THRESHOLD_PCT = float(os.getenv("DISK_THRESHOLD_PCT", "90"))

# ── Stocks list ───────────────────────────────────────────────────────────────
STOCK_TICKERS = os.getenv("STOCK_TICKERS",
    "AAPL,MSFT,GOOGL,AMZN,NVDA,META,TSLA,AMD,INTC,ORCL,"
    "NFLX,PYPL,CRM,SHOP,SQ,COIN,PLTR,ARM,SMCI,TSM,"
    "ASML,QCOM,AVGO,MU,AMAT"
).split(",")

# FX pairs and precious metals (yfinance symbols)
FX_PAIRS      = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "USDCAD=X", "AUDUSD=X"]
METAL_TICKERS = ["GC=F", "SI=F"]   # Gold futures, Silver futures

_FX_LABELS_MAP = {
    "EURUSD=X": "EUR/USD", "GBPUSD=X": "GBP/USD",
    "USDJPY=X": "USD/JPY", "USDCAD=X": "USD/CAD", "AUDUSD=X": "AUD/USD",
}
_METAL_LABELS_MAP = {"GC=F": "Gold (oz)", "SI=F": "Silver (oz)"}

# ── Mailman key-people list ────────────────────────────────────────────────────
KEY_PEOPLE = [e.strip() for e in
              os.getenv("KEY_PEOPLE", "").split(",") if e.strip()]

# ── Hacker Digest config ───────────────────────────────────────────────────────
HACKER_STORIES_FETCH  = int(os.getenv("HACKER_STORIES_FETCH",  "30"))
HACKER_STORIES_CURATE = int(os.getenv("HACKER_STORIES_CURATE", "10"))
