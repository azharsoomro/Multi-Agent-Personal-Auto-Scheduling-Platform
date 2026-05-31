"""APScheduler integration — cron-based agent scheduling with resource awareness."""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
import logging

from config import AGENT_SCHEDULES
from database import get_db, log_agent

logger = logging.getLogger(__name__)
_scheduler: BackgroundScheduler | None = None


def _make_job(agent_name: str):
    def _job():
        # import here to avoid circular imports at module load
        from orchestrator import trigger_agent
        result = trigger_agent(agent_name)
        with get_db() as db:
            log_agent(db, "scheduler", "INFO",
                      f"Scheduled trigger for {agent_name}: {result.get('status')}")
    _job.__name__ = f"job_{agent_name}"
    return _job


def _on_job_event(event):
    if event.exception:
        logger.error(f"Scheduler job failed: {event.job_id} — {event.exception}")


def start_scheduler() -> BackgroundScheduler:
    global _scheduler
    _scheduler = BackgroundScheduler(timezone="UTC", job_defaults={"misfire_grace_time": 60})
    _scheduler.add_listener(_on_job_event, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)

    for agent_name, cron_expr in AGENT_SCHEDULES.items():
        parts = cron_expr.split()
        if len(parts) != 5:
            logger.warning(f"Invalid cron for {agent_name}: {cron_expr}")
            continue
        minute, hour, day, month, day_of_week = parts
        trigger = CronTrigger(
            minute=minute, hour=hour, day=day,
            month=month, day_of_week=day_of_week, timezone="UTC"
        )
        _scheduler.add_job(
            _make_job(agent_name),
            trigger=trigger,
            id=f"agent_{agent_name}",
            replace_existing=True,
        )
        logger.info(f"Scheduled {agent_name} with cron: {cron_expr}")

    _scheduler.start()
    return _scheduler


def get_jobs() -> list[dict]:
    if not _scheduler:
        return []
    jobs = []
    for job in _scheduler.get_jobs():
        next_run = job.next_run_time
        jobs.append({
            "id":       job.id,
            "name":     job.name or job.id,
            "next_run": next_run.isoformat() if next_run else None,
            "trigger":  str(job.trigger),
        })
    return jobs


def update_schedule(agent_name: str, cron_expr: str) -> bool:
    if not _scheduler:
        return False
    job_id = f"agent_{agent_name}"
    parts = cron_expr.split()
    if len(parts) != 5:
        return False
    minute, hour, day, month, day_of_week = parts
    try:
        _scheduler.reschedule_job(
            job_id,
            trigger=CronTrigger(minute=minute, hour=hour, day=day,
                                month=month, day_of_week=day_of_week, timezone="UTC")
        )
        return True
    except Exception:
        return False


def stop_scheduler():
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
