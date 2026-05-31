"""Abstract base for all agents — handles run-record lifecycle."""
import abc
import time
from datetime import datetime
from database import get_db, AgentRun, log_agent


class BaseAgent(abc.ABC):
    name: str = "base"

    def run(self) -> dict:
        started = datetime.utcnow()
        with get_db() as db:
            run = AgentRun(agent_name=self.name, status="running", started_at=started)
            db.add(run)
            db.flush()
            run_id = run.id

        t0 = time.time()
        result = {}
        try:
            with get_db() as db:
                log_agent(db, self.name, "INFO", f"Agent started")
            result = self._execute()
            status = "success"
        except Exception as e:
            status = "failed"
            result = {"error": str(e)}
            with get_db() as db:
                log_agent(db, self.name, "ERROR", str(e))
        finally:
            elapsed = round(time.time() - t0, 2)
            with get_db() as db:
                run = db.get(AgentRun, run_id)
                if run:
                    run.status = status
                    run.finished_at = datetime.utcnow()
                    run.duration_s = elapsed
                    run.message = result.get("summary", result.get("error", ""))
                    run.meta = result
                log_agent(db, self.name, "INFO",
                          f"Agent finished in {elapsed}s — {status}")
        return result

    @abc.abstractmethod
    def _execute(self) -> dict:
        """Override in subclasses. Return a dict summary."""
