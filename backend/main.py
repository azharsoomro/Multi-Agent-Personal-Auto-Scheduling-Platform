"""
Multi-Agent Auto-Scheduling Platform — FastAPI backend
WebSocket at /ws broadcasts real-time events to the dashboard.
"""
import asyncio
import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from database import (init_db, get_db, AgentRun, AgentLog, StockSnapshot, EmailRecord,
                      SystemMetric, VideoRecord, HNStoryRecord, MarketCommentary, MailmanRecord)
from orchestrator import (
    trigger_agent, get_agent_status, get_orchestrator_status,
    set_broadcast, start_metrics_collector, stop as stop_orchestrator,
)
from scheduler import start_scheduler, stop_scheduler, get_jobs, update_schedule
from llm_client import is_ollama_running, list_models

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ── WebSocket connection manager ──────────────────────────────────────────────
class ConnectionManager:
    def __init__(self):
        self._conns: list[WebSocket] = []
        self._lock  = asyncio.Lock()
        self._queue: asyncio.Queue = None  # set after event loop starts

    def init_queue(self):
        self._queue = asyncio.Queue()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        async with self._lock:
            self._conns.append(ws)

    async def disconnect(self, ws: WebSocket):
        async with self._lock:
            self._conns = [c for c in self._conns if c is not ws]

    async def broadcast(self, data: dict):
        text = json.dumps(data)
        async with self._lock:
            dead = []
            for ws in self._conns:
                try:
                    await ws.send_text(text)
                except Exception:
                    dead.append(ws)
            self._conns = [c for c in self._conns if c not in dead]

    def enqueue(self, data: dict):
        """Called from sync threads — puts event into async queue."""
        if self._queue:
            try:
                self._queue.put_nowait(data)
            except asyncio.QueueFull:
                pass


manager = ConnectionManager()


async def _ws_relay():
    """Async task that drains the sync→async event queue."""
    while True:
        try:
            data = await asyncio.wait_for(manager._queue.get(), timeout=1.0)
            await manager.broadcast(data)
        except asyncio.TimeoutError:
            pass
        except Exception as e:
            logger.warning(f"WS relay error: {e}")


# ── App lifespan ──────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    manager.init_queue()
    set_broadcast(manager.enqueue)
    start_metrics_collector()
    start_scheduler()
    asyncio.create_task(_ws_relay())
    logger.info("Multi-Agent Platform started")
    yield
    stop_scheduler()
    stop_orchestrator()
    logger.info("Platform stopped")


app = FastAPI(title="Multi-Agent Platform", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.middleware("http")
async def _no_cache_static(request, call_next):
    """Force browsers to always re-fetch the dashboard assets — no stale UI."""
    response = await call_next(request)
    if request.url.path.startswith("/static") or request.url.path == "/":
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


# ── WebSocket ─────────────────────────────────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        # send current state on connect
        await ws.send_text(json.dumps({
            "event": "init",
            "data":  get_orchestrator_status(),
            "agents": get_agent_status(),
        }))
        while True:
            await ws.receive_text()   # keep alive (client pings)
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(ws)


# ── REST endpoints ────────────────────────────────────────────────────────────
@app.get("/")
def serve_dashboard():
    return FileResponse(
        str(FRONTEND_DIR / "index.html"),
        headers={"Cache-Control": "no-store, no-cache, must-revalidate"}
    )


@app.get("/api/status")
def api_status():
    return {**get_orchestrator_status(), "agents": get_agent_status()}


@app.get("/api/agents")
def api_agents():
    return get_agent_status()


class TriggerRequest(BaseModel):
    force: bool = False

@app.post("/api/agents/{agent_name}/trigger")
def api_trigger(agent_name: str, body: TriggerRequest = TriggerRequest()):
    result = trigger_agent(agent_name, force=body.force)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@app.get("/api/scheduler/jobs")
def api_jobs():
    return get_jobs()


class ScheduleUpdate(BaseModel):
    cron: str

@app.put("/api/scheduler/{agent_name}")
def api_update_schedule(agent_name: str, body: ScheduleUpdate):
    ok = update_schedule(agent_name, body.cron)
    if not ok:
        raise HTTPException(status_code=400, detail="Invalid cron expression or unknown agent")
    return {"status": "updated", "agent": agent_name, "cron": body.cron}


@app.get("/api/logs")
def api_logs(agent: str = Query(None), limit: int = Query(100, le=500)):
    with get_db() as db:
        q = db.query(AgentLog).order_by(AgentLog.created_at.desc())
        if agent:
            q = q.filter_by(agent_name=agent)
        rows = q.limit(limit).all()
        return [{"id": r.id, "agent": r.agent_name, "level": r.level,
                 "message": r.message, "ts": r.created_at.isoformat()} for r in rows]


@app.get("/api/runs")
def api_runs(agent: str = Query(None), limit: int = Query(50, le=200)):
    with get_db() as db:
        q = db.query(AgentRun).order_by(AgentRun.started_at.desc())
        if agent:
            q = q.filter_by(agent_name=agent)
        rows = q.limit(limit).all()
        return [{
            "id": r.id, "agent": r.agent_name, "status": r.status,
            "started": r.started_at.isoformat(),
            "finished": r.finished_at.isoformat() if r.finished_at else None,
            "duration_s": r.duration_s, "message": r.message,
        } for r in rows]


@app.get("/api/stocks")
def api_stocks(ticker: str = Query(None), limit: int = Query(100, le=500)):
    with get_db() as db:
        q = db.query(StockSnapshot).order_by(StockSnapshot.captured_at.desc())
        if ticker:
            q = q.filter_by(ticker=ticker)
        rows = q.limit(limit).all()
        return [{
            "ticker": r.ticker, "price": r.price, "change_pct": r.change_pct,
            "volume": r.volume, "captured_at": r.captured_at.isoformat(),
        } for r in rows]


@app.get("/api/emails")
def api_emails(limit: int = Query(50, le=200)):
    with get_db() as db:
        rows = db.query(EmailRecord).order_by(EmailRecord.sent_at.desc()).limit(limit).all()
        return [{"id": r.id, "agent": r.agent_name, "subject": r.subject,
                 "recipient": r.recipient, "sent_at": r.sent_at.isoformat(),
                 "success": r.success} for r in rows]


@app.get("/api/metrics/history")
def api_metrics_history(limit: int = Query(60, le=300)):
    with get_db() as db:
        rows = db.query(SystemMetric).order_by(SystemMetric.captured_at.desc()).limit(limit).all()
        result = [{"cpu": r.cpu_pct, "ram": r.ram_pct, "disk": r.disk_pct,
                   "ts": r.captured_at.isoformat()} for r in rows]
    return list(reversed(result))


@app.get("/api/ollama/status")
def api_ollama_status():
    return {"running": is_ollama_running(), "models": list_models()}


def _pct_delta(cur: int, prev: int) -> float:
    if prev == 0:
        return 100.0 if cur > 0 else 0.0
    return round((cur - prev) / prev * 100, 1)


@app.get("/api/dashboard/stats")
def api_dashboard_stats():
    """Aggregate KPIs + trend deltas + cost-avoided for the operations dashboard."""
    from datetime import datetime, timedelta
    from llm_client import get_stats as _llm_stats

    now = datetime.utcnow()
    d1, d2 = now - timedelta(days=1), now - timedelta(days=2)

    with get_db() as db:
        runs = db.query(AgentRun).all()
        total_runs   = len(runs)
        success_runs = len([r for r in runs if r.status == "success"])
        failed_runs  = len([r for r in runs if r.status in ("failed", "crashed")])
        durations    = [r.duration_s for r in runs if r.duration_s]
        avg_dur      = round(sum(durations) / len(durations), 2) if durations else 0

        runs_today = len([r for r in runs if r.started_at and r.started_at >= d1])
        runs_prev  = len([r for r in runs if r.started_at and d2 <= r.started_at < d1])
        succ_today = len([r for r in runs if r.started_at and r.started_at >= d1 and r.status == "success"])
        succ_prev  = len([r for r in runs if r.started_at and d2 <= r.started_at < d1 and r.status == "success"])

        total_emails = db.query(EmailRecord).count()
        total_stocks = db.query(StockSnapshot).count()
        total_videos = db.query(VideoRecord).count()
        total_stories= db.query(HNStoryRecord).count()
        total_mails  = db.query(MailmanRecord).count()

    llm = _llm_stats()
    live_calls  = llm.get("total", 0)
    llm_avg_ms  = llm.get("avg_ms", 0)
    llm_errors  = llm.get("errors", 0)

    # Durable estimate of cumulative LLM calls from DB content (survives restarts).
    # Per-agent call factors: ai_times=1 intro, wallstreet=1 commentary,
    # hacker=1 overview + 1 per story, mailman=1 per classified email.
    with get_db() as db:
        n_ai    = db.query(AgentRun).filter_by(agent_name="ai_times").count()
        n_ws    = db.query(AgentRun).filter_by(agent_name="wallstreet_wolf").count()
        n_hd    = db.query(AgentRun).filter_by(agent_name="hacker_digest").count()
    est_calls = (n_ai * 1) + (n_ws * 1) + (n_hd * 1) + total_stories + total_mails
    llm_calls = max(est_calls, live_calls)

    # Estimated tokens & cloud-cost avoided (GPT-4-class blended rate)
    est_tokens  = llm_calls * 850          # ~850 tokens / call (prompt+completion)
    cost_per_call = 0.03                   # blended GPT-4-class $/call
    cost_avoided = round(llm_calls * cost_per_call, 2)

    return {
        "total_runs": total_runs,
        "success_runs": success_runs,
        "failed_runs": failed_runs,
        "success_rate": round(success_runs / total_runs * 100, 1) if total_runs else 100.0,
        "avg_duration_s": avg_dur,
        "runs_today": runs_today,
        "runs_delta": _pct_delta(runs_today, runs_prev),
        "success_delta": _pct_delta(succ_today, succ_prev),
        "total_emails": total_emails,
        "total_stocks": total_stocks,
        "total_videos": total_videos,
        "total_stories": total_stories,
        "total_classified": total_mails,
        "llm_calls": llm_calls,
        "llm_avg_ms": llm_avg_ms,
        "llm_errors": llm_errors,
        "est_tokens": est_tokens,
        "cost_avoided": cost_avoided,
        "cost_per_call": cost_per_call,
    }


@app.get("/api/dashboard/agent-perf")
def api_agent_perf():
    """Per-agent run counts, success rate, and recent durations for sparklines."""
    with get_db() as db:
        out = []
        for name in ("ai_times", "mailman", "wallstreet_wolf", "hacker_digest"):
            rows = (db.query(AgentRun).filter_by(agent_name=name)
                    .order_by(AgentRun.started_at.desc()).limit(12).all())
            total = db.query(AgentRun).filter_by(agent_name=name).count()
            succ  = db.query(AgentRun).filter_by(agent_name=name, status="success").count()
            spark = [round(r.duration_s, 1) for r in reversed(rows) if r.duration_s]
            out.append({
                "agent": name,
                "runs": total,
                "success_rate": round(succ / total * 100) if total else 0,
                "spark": spark or [1],
            })
    return out


# ── AI-Times endpoints ────────────────────────────────────────────────────────
@app.get("/api/ai-times/videos")
def api_aitimes_videos(category: str = Query(None), limit: int = Query(20, le=100)):
    with get_db() as db:
        q = db.query(VideoRecord).order_by(VideoRecord.fetched_at.desc())
        if category:
            q = q.filter_by(category=category)
        rows = q.limit(limit).all()
        return [{"id": r.id, "title": r.title, "channel": r.channel, "url": r.url,
                 "thumbnail": r.thumbnail, "description": r.description,
                 "published": r.published, "category": r.category,
                 "fetched_at": r.fetched_at.isoformat()} for r in rows]


# ── Mailman endpoints ─────────────────────────────────────────────────────────
@app.get("/api/mailman/records")
def api_mailman_records(limit: int = Query(50, le=200)):
    with get_db() as db:
        rows = db.query(MailmanRecord).order_by(MailmanRecord.processed_at.desc()).limit(limit).all()
        return [{"id": r.id, "subject": r.subject, "sender": r.sender,
                 "category": r.category, "priority": r.priority,
                 "summary": r.llm_summary, "starred": r.starred,
                 "processed_at": r.processed_at.isoformat()} for r in rows]


@app.get("/api/mailman/stats")
def api_mailman_stats():
    with get_db() as db:
        rows = db.query(MailmanRecord).all()
        counts: dict = {}
        for r in rows:
            counts[r.category] = counts.get(r.category, 0) + 1
        return {"total": len(rows), "by_category": counts}


# ── Wallstreet Wolf endpoints ─────────────────────────────────────────────────
@app.get("/api/wallstreet/commentary")
def api_wallstreet_commentary():
    with get_db() as db:
        row = db.query(MarketCommentary).order_by(MarketCommentary.created_at.desc()).first()
        if not row:
            return {"commentary": None, "created_at": None}
        return {"commentary": row.commentary, "created_at": row.created_at.isoformat()}


@app.get("/api/wallstreet/metals")
def api_metals():
    from config import METAL_TICKERS, _METAL_LABELS_MAP
    with get_db() as db:
        results = []
        for sym in METAL_TICKERS:
            row = (db.query(StockSnapshot).filter_by(ticker=sym)
                   .order_by(StockSnapshot.captured_at.desc()).first())
            if row:
                results.append({"ticker": sym, "label": _METAL_LABELS_MAP.get(sym, sym),
                                 "price": row.price, "change_pct": row.change_pct,
                                 "captured_at": row.captured_at.isoformat()})
        return results


@app.get("/api/wallstreet/fx")
def api_fx():
    from config import FX_PAIRS, _FX_LABELS_MAP
    with get_db() as db:
        results = []
        for sym in FX_PAIRS:
            row = (db.query(StockSnapshot).filter_by(ticker=sym)
                   .order_by(StockSnapshot.captured_at.desc()).first())
            if row:
                results.append({"ticker": sym, "label": _FX_LABELS_MAP.get(sym, sym),
                                 "price": row.price, "change_pct": row.change_pct,
                                 "captured_at": row.captured_at.isoformat()})
        return results


# ── Hacker Digest endpoints ───────────────────────────────────────────────────
@app.get("/api/hacker-digest/stories")
def api_hn_stories(limit: int = Query(10, le=50)):
    with get_db() as db:
        rows = db.query(HNStoryRecord).order_by(HNStoryRecord.fetched_at.desc()).limit(limit).all()
        return [{"id": r.id, "hn_id": r.hn_id, "title": r.title, "url": r.url,
                 "score": r.score, "comments": r.comments, "by": r.by,
                 "hn_url": r.hn_url, "takeaway": r.takeaway,
                 "fetched_at": r.fetched_at.isoformat()} for r in rows]


# ── Config endpoints (key-people + hacker digest params) ──────────────────────
@app.get("/api/config/key-people")
def api_get_key_people():
    from config import KEY_PEOPLE
    return {"key_people": KEY_PEOPLE}


class KeyPeopleUpdate(BaseModel):
    key_people: list[str]

@app.put("/api/config/key-people")
def api_set_key_people(body: KeyPeopleUpdate):
    import config as _cfg
    _cfg.KEY_PEOPLE = [e.strip() for e in body.key_people if e.strip()]
    return {"key_people": _cfg.KEY_PEOPLE}


@app.get("/api/config/hacker-digest")
def api_get_hd_config():
    from config import HACKER_STORIES_FETCH, HACKER_STORIES_CURATE
    return {"fetch": HACKER_STORIES_FETCH, "curate": HACKER_STORIES_CURATE}


class HDConfigUpdate(BaseModel):
    fetch: int = 30
    curate: int = 10

@app.put("/api/config/hacker-digest")
def api_set_hd_config(body: HDConfigUpdate):
    import config as _cfg
    _cfg.HACKER_STORIES_FETCH  = max(10, min(100, body.fetch))
    _cfg.HACKER_STORIES_CURATE = max(5,  min(30,  body.curate))
    return {"fetch": _cfg.HACKER_STORIES_FETCH, "curate": _cfg.HACKER_STORIES_CURATE}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False, log_level="info")
