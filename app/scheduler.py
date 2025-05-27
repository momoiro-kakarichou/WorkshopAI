from apscheduler.schedulers.background import BackgroundScheduler
from typing import Callable, Dict, Optional
from flask import Flask
from functools import partial
from app.extensions import log

class CyclicTaskManager:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        self.tasks: Dict[str, Callable] = {}
        self.app: Optional[Flask] = None
        
    def init_app(self, app: Flask):
        self.app = app

    def add_task(self, task_id: str, task: Callable, interval: float):
        if not self.app:
            raise RuntimeError("CyclicTaskManager must be initialized with init_app() before adding tasks.")

        if task_id in self.tasks:
            log.warning(f"Task with id '{task_id}' already exists. It will be replaced.")
            self.remove_task(task_id)

        self.tasks[task_id] = task
        wrapped_task = partial(self._run_task_with_context, task_func=task, task_id=task_id)

        try:
            self.scheduler.add_job(
                func=wrapped_task,
                trigger='interval',
                seconds=interval,
                id=task_id,
                name=f"Flask Task: {task_id}"
            )
        except Exception:
            if task_id in self.tasks:
                del self.tasks[task_id]

    def remove_task(self, task_id: str):
        if task_id in self.tasks:
            del self.tasks[task_id]
            try:
                self.scheduler.remove_job(task_id)
            except Exception:
                log.exception(f"Error removing job '{task_id}' from scheduler.")
        else:
            log.debug(f"Attempted to remove non-existent task '{task_id}'.")

    def stop(self):
        try:
            self.scheduler.shutdown(wait=False)
        except Exception:
            log.exception("Error during scheduler shutdown.")
        self.tasks.clear()
        
    def _run_task_with_context(self, task_func: Callable, task_id: str):
        if not self.app:
            return

        with self.app.app_context():
            try:
                task_func()
            except Exception as e:
                print(e)