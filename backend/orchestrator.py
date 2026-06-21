"""
Main Orchestrator — manages agent lifecycle, system resources, LLM scheduling,
deadlock prevention, and broadcasts state over WebSocket.
"""
import threading
import time
import psutil
from datetime import datetime
from typing import Callable

from agents.ai_times import AITimesAgent
from agents.mailman import MailmanAgent
from agents.wallstreet_wolf import WallstreetWolfAgent
from agents.hacker_digest import HackerDigestAgent
from database import get_db, SystemMetric, AgentRun, log_agent
from llm_client import get_stats as llm_stats, is_ollama_running
from config import CPU_THRESHOLD_PCT, RAM_THRESHOLD_PCT, DISK_THRESHOLD_PCT

AGENTS = {
    "ai_times":        AITimesAgent(),
    "mailman":         MailmanAgent(),
    "wallstreet_wolf": WallstreetWolfAgent(),
    "hacker_digest":   HackerDigestAgent(),
}

_running_agents: set[str] = set()
_agent_threads: dict[str, threading.Thread] = {}   # track live threads for watchdog
_agent_lock = threading.Lock()
_broadcast_fn: Callable | None = None    # set by main.py WebSocket handler
_stop_event = threading.Event()


def set_broadcast(fn: Callable):
    global _broadcast_fn
    _broadcast_fn = fn


def _broadcast(event: str, data: dict):
    if _broadcast_fn:
        try:
            _broadcast_fn({"event": event, "data": data, "ts": datetime.utcnow().isoformat()})
        except Exception:
            pass


def get_system_metrics() -> dict:
    import os
    cpu  = psutil.cpu_percent(interval=0.3)
    ram  = psutil.virtual_memory()
    _disk_path = "C:\\" if os.name == "nt" else "/"
    disk = psutil.disk_usage(_disk_path)
    threads = threading.active_count()
    return {
        "cpu_pct":      cpu,
        "ram_pct":      ram.percent,
        "ram_used_gb":  round(ram.used / 1e9, 2),
        "ram_total_gb": round(ram.total / 1e9, 2),
        "disk_pct":     disk.percent,
        "disk_used_gb": round(disk.used / 1e9, 2),
        "disk_total_gb":round(disk.total / 1e9, 2),
        "threads":      threads,
    }


def _check_resources() -> tuple[bool, str]:
    """Return (ok, reason). ok=False means resources are too stressed to run LLM."""
    m = get_system_metrics()
    if m["cpu_pct"] > CPU_THRESHOLD_PCT:
        return False, f"CPU at {m['cpu_pct']}% (limit {CPU_THRESHOLD_PCT}%)"
    if m["ram_pct"] > RAM_THRESHOLD_PCT:
        return False, f"RAM at {m['ram_pct']}% (limit {RAM_THRESHOLD_PCT}%)"
    if m["disk_pct"] > DISK_THRESHOLD_PCT:
        return False, f"Disk at {m['disk_pct']}% (limit {DISK_THRESHOLD_PCT}%)"
    return True, "ok"


def trigger_agent(agent_name: str, force: bool = False) -> dict:
    """Launch an agent in a background thread. Prevents double-runs."""
    if agent_name not in AGENTS:
        return {"error": f"Unknown agent: {agent_name}"}

    with _agent_lock:
        if agent_name in _running_agents:
            return {"status": "already_running", "agent": agent_name}
        _running_agents.add(agent_name)

    if not force:
        ok, reason = _check_resources()
        if not ok:
            with _agent_lock:
                _running_agents.discard(agent_name)
            msg = f"Resources constrained — {reason}. Use force=true to override."
            with get_db() as db:
                log_agent(db, "orchestrator", "WARN", msg)
            return {"status": "skipped", "reason": msg}

    if not is_ollama_running():
        with _agent_lock:
            _running_agents.discard(agent_name)
        return {"status": "skipped", "reason": "Ollama is not running"}

    def _run():
        _broadcast("agent_started", {"agent": agent_name})
        try:
            result = AGENTS[agent_name].run()
            _broadcast("agent_finished", {"agent": agent_name, "result": result})
        except Exception as e:
            _broadcast("agent_error", {"agent": agent_name, "error": str(e)})
        finally:
            with _agent_lock:
                _running_agents.discard(agent_name)
                _agent_threads.pop(agent_name, None)

    t = threading.Thread(target=_run, name=f"agent-{agent_name}", daemon=True)
    with _agent_lock:
        _agent_threads[agent_name] = t
    t.start()
    return {"status": "started", "agent": agent_name}


def get_agent_status() -> dict:
    with get_db() as db:
        status = {}
        for name in AGENTS:
            last = (
                db.query(AgentRun)
                .filter_by(agent_name=name)
                .order_by(AgentRun.started_at.desc())
                .first()
            )
            status[name] = {
                "running":     name in _running_agents,
                "last_run":    last.started_at.isoformat() if last else None,
                "last_status": last.status if last else "never",
                "last_msg":    last.message if last else None,
                "duration_s":  last.duration_s if last else None,
            }
    return status


def get_orchestrator_status() -> dict:
    metrics = get_system_metrics()
    resource_ok, resource_msg = _check_resources()
    return {
        "ollama_running": is_ollama_running(),
        "resource_ok":    resource_ok,
        "resource_msg":   resource_msg,
        "running_agents": list(_running_agents),
        "llm_stats":      llm_stats(),
        "metrics":        metrics,
        "agent_count":    len(AGENTS),
        "timestamp":      datetime.utcnow().isoformat(),
    }


def _metrics_collector():
    """Background thread: broadcasts system metrics every 5s; saves to DB every 60s."""
    _db_tick = 0
    while not _stop_event.wait(5):
        m = get_system_metrics()
        _db_tick += 1
        if _db_tick >= 12:   # every 60s
            _db_tick = 0
            try:
                with get_db() as db:
                    db.add(SystemMetric(
                        cpu_pct=m["cpu_pct"],
                        ram_pct=m["ram_pct"],
                        disk_pct=m["disk_pct"],
                        ram_used_gb=m["ram_used_gb"],
                    ))
            except Exception:
                pass
        _broadcast("metrics", m)


def _agent_watchdog():
    """Background thread: detects crashed agent threads and cleans up state."""
    while not _stop_event.wait(10):
        with _agent_lock:
            crashed = [
                name for name, t in list(_agent_threads.items())
                if not t.is_alive()
            ]
        for name in crashed:
            with _agent_lock:
                _running_agents.discard(name)
                _agent_threads.pop(name, None)
            try:
                with get_db() as db:
                    from database import AgentRun
                    run = (db.query(AgentRun)
                           .filter_by(agent_name=name, status="running")
                           .order_by(AgentRun.started_at.desc()).first())
                    if run:
                        run.status = "crashed"
                        run.message = "Thread died unexpectedly — auto-recovered"
                    log_agent(db, "orchestrator", "WARN",
                              f"Agent {name} thread crashed — state recovered")
            except Exception:
                pass
            _broadcast("agent_crashed", {"agent": name})


def start_metrics_collector():
    threading.Thread(target=_metrics_collector, name="metrics-collector", daemon=True).start()
    threading.Thread(target=_agent_watchdog,    name="agent-watchdog",    daemon=True).start()


def stop():
    _stop_event.set()
