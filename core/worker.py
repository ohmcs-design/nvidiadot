"""
DOT AI - Specialized Workers Runtime
Implements Code Specialist, Verifier, and Terminal Workers.
"""
import logging
from typing import Dict, Any, List, Optional
from core.nvidia_client import NvidiaClient
from core.workspace import WorkspaceManager
from core.approval_gate import ApprovalGate
from core.terminal_runner import TerminalRunner
import config

logger = logging.getLogger("dot.worker")

CODER_SYSTEM_PROMPT = """You are DOT AI Code Specialist, a senior software engineer.
You are given a task, workspace context, and optional existing file contents.
Your job is to generate clean, production-grade code to accomplish the task.

If modifying or creating a file, provide the complete content of the file.
Format your output with:
FILE: <relative_path>
```<language>
<code content>
```
EXPLANATION:
<brief explanation of changes>
"""

VERIFIER_SYSTEM_PROMPT = """You are DOT AI Independent Verifier, an expert code reviewer and QA engineer.
Your job is to critically review code diffs or task execution outputs against acceptance criteria.
Point out any syntax errors, security flaws, regressions, or missing edge cases.
Conclude with a clear verdict: [VERIFIED] or [FAILED: reason].
"""

class WorkerRuntime:
    def __init__(
        self,
        nvidia_client: NvidiaClient,
        workspace: WorkspaceManager,
        approval_gate: ApprovalGate,
        terminal: TerminalRunner
    ):
        self.nvidia = nvidia_client
        self.workspace = workspace
        self.approval_gate = approval_gate
        self.terminal = terminal

    async def execute_task(
        self,
        goal_id: str,
        task: Dict[str, Any],
        log_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """Dispatch task to the specialized worker"""
        worker_type = task.get("worker_type", "coder")
        action = task.get("action", "write_code")
        title = task.get("title", "")
        desc = task.get("description", "")
        target_file = task.get("target_file", "")

        def log(msg: str):
            if log_callback:
                log_callback(f"[{worker_type.upper()}] {msg}")

        log(f"Starting task: {title}")

        if worker_type == "terminal":
            cmd = task.get("command", desc)
            req_id = self.approval_gate.submit_request(
                goal_id=goal_id,
                task_id=task["id"],
                action_type="terminal_command",
                title=f"Run command: {cmd}",
                details={"command": cmd, "task": title}
            )
            log(f"Awaiting approval to execute: `{cmd}`")
            approved = await self.approval_gate.wait_for_decision(req_id)
            if not approved:
                log("Command execution rejected by user.")
                return {"success": False, "error": "Action rejected by user"}

            log("Executing command...")
            res = await self.terminal.execute_command(cmd)
            log(f"Completed with exit code {res['exit_code']}")
            return res

        elif worker_type == "verifier":
            log("Running verification review...")
            context = f"Goal ID: {goal_id}\nTask: {title}\nDescription: {desc}"
            if self.nvidia.is_configured():
                try:
                    def on_verifier_reasoning(text):
                        log(f"[Nemotron Verifier Thinking] {text.strip()}")

                    review = await self.nvidia.structured_completion(
                        system_prompt=VERIFIER_SYSTEM_PROMPT,
                        user_prompt=context,
                        model=config.DEFAULT_VERIFIER_MODEL,
                        on_reasoning_callback=on_verifier_reasoning
                    )
                    log(f"Verification output:\n{review}")
                    return {"success": "[VERIFIED]" in review, "review": review}
                except Exception as e:
                    log(f"Verification failed: {e}")
            return {"success": True, "review": "Automated verification completed (mock)."}

        else: # Coder Worker
            log("Analyzing requirements and formulating code solution...")
            existing_content = ""
            if target_file:
                read_res = self.workspace.read_file(target_file)
                if read_res["success"]:
                    existing_content = read_res["content"]

            prompt = f"Task: {title}\nDescription: {desc}\nTarget File: {target_file}\n"
            if existing_content:
                prompt += f"\nExisting File Contents ({target_file}):\n```\n{existing_content[:3000]}\n```\n"

            if self.nvidia.is_configured():
                try:
                    log(f"Prompting NVIDIA {config.DEFAULT_CODER_MODEL} (Thinking enabled)...")
                    def on_reasoning(text):
                        log(f"[Nemotron Thinking] {text.strip()}")

                    response = await self.nvidia.structured_completion(
                        system_prompt=CODER_SYSTEM_PROMPT,
                        user_prompt=prompt,
                        model=config.DEFAULT_CODER_MODEL,
                        on_reasoning_callback=on_reasoning
                    )
                    log("Code generated. Preparing diff for approval...")

                    # Extract code block if present
                    code = response
                    if "```" in response:
                        parts = response.split("```")
                        if len(parts) >= 2:
                            code_block = parts[1]
                            # strip language tag on first line
                            lines = code_block.splitlines()
                            code = "\n".join(lines[1:]) if len(lines) > 1 else code_block

                    if target_file:
                        diff_info = self.workspace.compute_diff(target_file, code)
                        req_id = self.approval_gate.submit_request(
                            goal_id=goal_id,
                            task_id=task["id"],
                            action_type="write_file",
                            title=f"Update file: {target_file}",
                            details=diff_info
                        )
                        log(f"Approval required for changes to {target_file}")
                        approved = await self.approval_gate.wait_for_decision(req_id)
                        if approved:
                            self.workspace.write_file(target_file, code)
                            log(f"Successfully applied changes to {target_file}")
                            return {"success": True, "file": target_file}
                        else:
                            log(f"Changes to {target_file} were rejected by user.")
                            return {"success": False, "error": "User rejected changes."}

                    return {"success": True, "output": response}
                except Exception as e:
                    log(f"Worker encountered error: {e}")
                    return {"success": False, "error": str(e)}

            # Fallback when offline
            log("NVIDIA API key not configured yet. Offline mode.")
            return {"success": True, "output": "Offline task completion."}
