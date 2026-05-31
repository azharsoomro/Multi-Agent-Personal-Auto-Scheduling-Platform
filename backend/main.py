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

from database import init_db, get_db, AgentRun, AgentLog, StockSnapshot, EmailRecord, SystemMetric
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
    return FileResponse(str(FRONTEND_DIR / "index.html"))


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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False, log_level="info")
