"""
DOT AI - Concurrency Scheduler & Task Orchestrator
Coordinates up to 5 goals concurrently, resolves dependencies, and emits state transitions.
"""
import asyncio
import logging
from typing import Dict, Any, List, Optional, Callable
from core.planner import GoalPlanner
from core.worker import WorkerRuntime
from core.checkpoint import CheckpointStore
import config

logger = logging.getLogger("dot.scheduler")

class Scheduler:
    def __init__(
        self,
        planner: GoalPlanner,
        worker_runtime: WorkerRuntime,
        store: CheckpointStore
    ):
        self.planner = planner
        self.worker_runtime = worker_runtime
        self.store = store
        self.active_goals: Dict[str, Dict[str, Any]] = {}
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.event_listeners: List[Callable[[Dict[str, Any]], None]] = []

    def add_listener(self, callback: Callable[[Dict[str, Any]], None]):
        self.event_listeners.append(callback)

    def emit_event(self, event_type: str, data: Dict[str, Any]):
        payload = {"type": event_type, "data": data}
        for cb in self.event_listeners:
            try:
                cb(payload)
            except Exception as e:
                logger.error(f"Event listener error: {e}")

    async def submit_goal(self, prompt: str, workspace_summary: str = "") -> Dict[str, Any]:
        """Submit a new goal for planning and execution"""
        if len([g for g in self.active_goals.values() if g["status"] in ("planning", "running")]) >= config.MAX_CONCURRENT_GOALS:
            return {"success": False, "error": f"Maximum limit of {config.MAX_CONCURRENT_GOALS} concurrent goals reached."}

        plan = await self.planner.create_plan(prompt, workspace_summary)
        goal_id = plan["id"]

        goal_data = {
            "id": goal_id,
            "title": plan["title"],
            "prompt": prompt,
            "status": "awaiting_approval",
            "progress": 0,
            "plan": plan,
            "logs": [],
            "completed_subtasks": []
        }

        self.active_goals[goal_id] = goal_data
        self.store.save_goal(goal_data)
        self.store.log_event("goal_planned", f"Goal planned: {plan['title']}", goal_id)
        self.emit_event("goal_created", goal_data)

        return {"success": True, "goal": goal_data}

    async def approve_and_start_goal(self, goal_id: str) -> bool:
        """Start execution of an approved goal plan"""
        if goal_id not in self.active_goals:
            return False

        goal = self.active_goals[goal_id]
        goal["status"] = "running"
        self.store.update_goal_status(goal_id, "running")
        self.emit_event("goal_updated", goal)

        task = asyncio.create_task(self._run_goal_loop(goal_id))
        self.running_tasks[goal_id] = task
        return True

    async def _run_goal_loop(self, goal_id: str):
        """Asynchronously executes subtasks respecting DAG dependencies"""
        goal = self.active_goals.get(goal_id)
        if not goal:
            return

        subtasks = goal["plan"].get("subtasks", [])
        completed_ids = set()

        def log_cb(msg: str):
            goal["logs"].append(msg)
            self.emit_event("goal_log", {"goal_id": goal_id, "log": msg})
            self.store.log_event("task_log", msg, goal_id)

        log_cb(f"Starting execution of goal '{goal['title']}' with {len(subtasks)} subtasks.")

        for task in subtasks:
            # Check dependencies
            deps = task.get("dependencies", [])
            for dep in deps:
                while dep not in completed_ids:
                    log_cb(f"Task '{task['title']}' blocked on dependency '{dep}'...")
                    await asyncio.sleep(1.0)

            # Mark task running
            task["status"] = "running"
            self.emit_event("task_updated", {"goal_id": goal_id, "task": task})

            res = await self.worker_runtime.execute_task(goal_id, task, log_callback=log_cb)

            if res.get("success", False):
                task["status"] = "completed"
                completed_ids.add(task["id"])
            else:
                task["status"] = "failed"
                task["error"] = res.get("error", "Unknown error")
                log_cb(f"Task '{task['title']}' failed: {task.get('error')}")

            # Update progress
            goal["progress"] = int((len(completed_ids) / len(subtasks)) * 100)
            self.emit_event("task_updated", {"goal_id": goal_id, "task": task})
            self.emit_event("goal_updated", goal)

        all_ok = len(completed_ids) == len(subtasks)
        goal["status"] = "completed" if all_ok else "failed"
        self.store.update_goal_status(goal_id, goal["status"])
        log_cb(f"Goal reached final state: {goal['status'].upper()}")
        self.emit_event("goal_updated", goal)

    def cancel_goal(self, goal_id: str) -> bool:
        if goal_id in self.running_tasks:
            self.running_tasks[goal_id].cancel()
        if goal_id in self.active_goals:
            self.active_goals[goal_id]["status"] = "cancelled"
            self.store.update_goal_status(goal_id, "cancelled")
            self.emit_event("goal_updated", self.active_goals[goal_id])
            return True
        return False
