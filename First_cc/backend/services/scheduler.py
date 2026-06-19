"""APScheduler-based cron trigger for MZC tasks."""
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from backend.services.task_store import TaskStore

logger = logging.getLogger(__name__)


class MzcScheduler:
    """Manages scheduled task execution.

    On reload_tasks():
    - Reads scheduled_tasks.json
    - Adds a cron job for each enabled task
    - Tick handler is set in Task 3.2 (anti-dual + execute)
    """

    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self._tick_handler = None  # set by set_tick_handler

    def start(self) -> None:
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Scheduler started")

    def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("Scheduler stopped")

    def set_tick_handler(self, handler) -> None:
        """Set the function called when a task fires.

        handler signature: handler(task_id: str, prompt: str) -> None
        """
        self._tick_handler = handler

    def reload_tasks(self) -> int:
        """Re-read JSON and rebuild all jobs. Returns count loaded."""
        # Remove all existing MZC jobs (by job id prefix)
        for job in list(self.scheduler.get_jobs()):
            if job.id.startswith("mzc:"):
                self.scheduler.remove_job(job.id)

        store = TaskStore()
        tasks = store.load_all()
        loaded = 0
        for task in tasks:
            if not task.enabled:
                continue
            try:
                trigger = CronTrigger.from_crontab(task.schedule)
            except Exception as e:
                logger.error(f"Invalid cron '{task.schedule}' for {task.id}: {e}")
                continue

            self.scheduler.add_job(
                self._on_tick,
                trigger=trigger,
                id=f"mzc:{task.id}",
                args=[task.id, task.prompt],
                replace_existing=True,
                max_instances=1,
                coalesce=True,
            )
            loaded += 1

        logger.info(f"Loaded {loaded} tasks into scheduler")
        return loaded

    def _on_tick(self, task_id: str, prompt: str) -> None:
        if self._tick_handler is None:
            logger.warning(f"Tick for {task_id} but no handler set; skipping")
            return
        try:
            self._tick_handler(task_id, prompt)
        except Exception:
            logger.exception(f"Tick handler error for {task_id}")

    def get_jobs(self) -> list[dict]:
        """Return list of {id, next_run, name} for inspection."""
        result = []
        for job in self.scheduler.get_jobs():
            result.append({
                "id": job.id.replace("mzc:", "", 1),
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                "name": job.name,
            })
        return result