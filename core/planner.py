"""
DOT AI - Goal Planner & Dependency Mapper
Generates task execution DAGs using NVIDIA NIM models with structured JSON schemas.
"""
import json
import uuid
import re
from typing import Dict, Any, List
from core.nvidia_client import NvidiaClient
import config

PLANNER_SYSTEM_PROMPT = """You are DOT AI Planner, an expert orchestrator for software engineering and technical work.
Your task is to take a user goal and workspace file context, and break it down into an ordered directed acyclic graph (DAG) of subtasks.

Return strictly a JSON object with this exact structure:
{
  "title": "Short title of the goal",
  "summary": "Brief explanation of the plan",
  "subtasks": [
    {
      "id": "task-1",
      "title": "Analyze existing code or files",
      "worker_type": "coder",
      "action": "analyze",
      "target_file": "path/to/file.py",
      "description": "Examine the file structure and requirements",
      "dependencies": []
    },
    {
      "id": "task-2",
      "title": "Write or refactor code",
      "worker_type": "coder",
      "action": "write_code",
      "target_file": "path/to/file.py",
      "description": "Implement the necessary changes or new logic",
      "dependencies": ["task-1"]
    },
    {
      "id": "task-3",
      "title": "Verify & test code",
      "worker_type": "verifier",
      "action": "test",
      "target_file": "path/to/test.py",
      "description": "Run tests or review code diffs",
      "dependencies": ["task-2"]
    }
  ]
}

Worker types must be one of: "coder", "verifier", "terminal".
Dependencies must be an array of prior subtask ids.
Do NOT wrap with markdown code fences, only output valid JSON.
"""

class GoalPlanner:
    def __init__(self, nvidia_client: NvidiaClient):
        self.nvidia = nvidia_client

    async def create_plan(self, prompt: str, workspace_summary: str) -> Dict[str, Any]:
        """Generate structured task DAG from user prompt"""
        user_msg = f"User Goal: {prompt}\n\nWorkspace File Tree & Context:\n{workspace_summary}"

        if self.nvidia.is_configured():
            try:
                raw_json = await self.nvidia.structured_completion(
                    system_prompt=PLANNER_SYSTEM_PROMPT,
                    user_prompt=user_msg,
                    model=config.DEFAULT_PLANNER_MODEL
                )
                # Clean any markdown code blocks
                clean = re.sub(r"^```json\s*|^```\s*|```$", "", raw_json.strip(), flags=re.MULTILINE)
                plan = json.loads(clean)
                plan["id"] = f"goal-{uuid.uuid4().hex[:8]}"
                plan["prompt"] = prompt
                return plan
            except Exception:
                pass

        # Offline / Fallback Plan Generator
        goal_id = f"goal-{uuid.uuid4().hex[:8]}"
        return {
            "id": goal_id,
            "title": prompt[:40] + ("..." if len(prompt) > 40 else ""),
            "prompt": prompt,
            "summary": "Plan generated based on goal description.",
            "subtasks": [
                {
                    "id": "task-1",
                    "title": "Inspect workspace files and dependencies",
                    "worker_type": "coder",
                    "action": "analyze",
                    "description": f"Examine files related to: {prompt}",
                    "dependencies": []
                },
                {
                    "id": "task-2",
                    "title": "Implement changes / generate code",
                    "worker_type": "coder",
                    "action": "write_code",
                    "description": f"Develop solution for: {prompt}",
                    "dependencies": ["task-1"]
                },
                {
                    "id": "task-3",
                    "title": "Review code diff & verify outcome",
                    "worker_type": "verifier",
                    "action": "review",
                    "description": "Verify code changes with independent checks.",
                    "dependencies": ["task-2"]
                }
            ]
        }
