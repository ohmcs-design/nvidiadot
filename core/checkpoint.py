"""
DOT AI - Persistence & Checkpoint Store (SQLite)
Maintains goals, subtasks, approvals, checkpoints, and event audits.
"""
import sqlite3
import json
import time
from typing import Dict, Any, List, Optional
import config

class CheckpointStore:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = str(db_path or config.DATABASE_PATH)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS goals (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                prompt TEXT NOT NULL,
                status TEXT NOT NULL,
                priority INTEGER DEFAULT 1,
                created_at REAL,
                updated_at REAL,
                plan_json TEXT
            );

            CREATE TABLE IF NOT EXISTS subtasks (
                id TEXT PRIMARY KEY,
                goal_id TEXT NOT NULL,
                title TEXT NOT NULL,
                worker_type TEXT NOT NULL,
                dependencies TEXT,
                status TEXT NOT NULL,
                result TEXT,
                FOREIGN KEY(goal_id) REFERENCES goals(id)
            );

            CREATE TABLE IF NOT EXISTS approvals (
                id TEXT PRIMARY KEY,
                goal_id TEXT NOT NULL,
                task_id TEXT,
                action_type TEXT NOT NULL,
                details_json TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at REAL,
                resolved_at REAL
            );

            CREATE TABLE IF NOT EXISTS checkpoints (
                id TEXT PRIMARY KEY,
                goal_id TEXT NOT NULL,
                state_snapshot TEXT NOT NULL,
                timestamp REAL
            );

            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                goal_id TEXT,
                event_type TEXT NOT NULL,
                message TEXT NOT NULL,
                details TEXT
            );
            """)

    def save_goal(self, goal_data: Dict[str, Any]):
        with self._get_conn() as conn:
            conn.execute("""
            INSERT OR REPLACE INTO goals (id, title, prompt, status, priority, created_at, updated_at, plan_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                goal_data["id"],
                goal_data["title"],
                goal_data.get("prompt", ""),
                goal_data.get("status", "draft"),
                goal_data.get("priority", 1),
                goal_data.get("created_at", time.time()),
                time.time(),
                json.dumps(goal_data.get("plan", {}))
            ))

    def update_goal_status(self, goal_id: str, status: str):
        with self._get_conn() as conn:
            conn.execute("UPDATE goals SET status = ?, updated_at = ? WHERE id = ?", (status, time.time(), goal_id))

    def get_all_goals(self) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            rows = conn.execute("SELECT * FROM goals ORDER BY created_at DESC").fetchall()
            goals = []
            for r in rows:
                g = dict(r)
                g["plan"] = json.loads(g["plan_json"]) if g.get("plan_json") else {}
                goals.append(g)
            return goals

    def log_event(self, event_type: str, message: str, goal_id: Optional[str] = None, details: Optional[Dict] = None):
        with self._get_conn() as conn:
            conn.execute("""
            INSERT INTO events (timestamp, goal_id, event_type, message, details)
            VALUES (?, ?, ?, ?, ?)
            """, (time.time(), goal_id, event_type, message, json.dumps(details or {})))

    def get_recent_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            rows = conn.execute("SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
            return [dict(r) for r in rows]
