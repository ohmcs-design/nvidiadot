"""
DOT AI - Desktop API Bridge
Exposes Python methods directly to the pywebview frontend window.
Uses a dedicated background event loop thread for thread-safe async execution.
"""
import os
import json
import asyncio
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional
import webview
from core.workspace import WorkspaceManager
from core.nvidia_client import NvidiaClient
from core.planner import GoalPlanner
from core.worker import WorkerRuntime
from core.scheduler import Scheduler
from core.approval_gate import ApprovalGate
from core.terminal_runner import TerminalRunner
from core.checkpoint import CheckpointStore
from core.chat_agent import ChatAgent
from core.web_inspector import WebInspector, LocalPreviewServer
import config

class DesktopAPIBridge:
    def __init__(self):
        self.window = None

        # Dedicated background async loop thread
        self._loop = asyncio.new_event_loop()
        self._loop_thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self._loop_thread.start()

        self.workspace = WorkspaceManager(None) # Starts with no folder selected; user picks manually
        self.nvidia = NvidiaClient()
        self.store = CheckpointStore()
        self.approval_gate = ApprovalGate()
        self.terminal = TerminalRunner(Path.cwd())
        self.web_inspector = WebInspector()
        self.local_server = LocalPreviewServer(os.getcwd())
        self.worker_runtime = WorkerRuntime(self.nvidia, self.workspace, self.approval_gate, self.terminal)
        self.planner = GoalPlanner(self.nvidia)
        self.scheduler = Scheduler(self.planner, self.worker_runtime, self.store)
        self.chat_agent = ChatAgent(self.nvidia, self.workspace, self.approval_gate, self.terminal, self.web_inspector)

        # Wire scheduler events to UI
        self.scheduler.add_listener(self._on_scheduler_event)

    def _run_event_loop(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def run_async(self, coro):
        """Thread-safe runner for coroutines from any pywebview thread"""
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result()

    def set_window(self, window):
        self.window = window

    def _on_scheduler_event(self, event: Dict[str, Any]):
        if self.window:
            js_code = f"if (window.onDotEvent) {{ window.onDotEvent({json.dumps(event)}); }}"
            try:
                self.window.evaluate_js(js_code)
            except Exception:
                pass

    # Workspace Methods
    def get_workspace_info(self) -> Dict[str, Any]:
        if not self.workspace.has_workspace:
            return {
                "has_folder": False,
                "root_path": "",
                "folder_name": "No Folder Opened",
                "terminal_cwd": str(self.terminal.cwd)
            }
        return {
            "has_folder": True,
            "root_path": str(self.workspace.root_path),
            "folder_name": self.workspace.root_path.name or str(self.workspace.root_path),
            "terminal_cwd": str(self.terminal.cwd)
        }

    def pick_folder(self) -> Dict[str, Any]:
        """Open native Windows folder dialog"""
        if not self.window:
            return {"success": False, "error": "No window"}
        result = self.window.create_file_dialog(webview.FOLDER_DIALOG)
        if result and len(result) > 0:
            folder = result[0]
            self.workspace.set_root(folder)
            self.terminal.set_cwd(Path(folder))
            if self.local_server.is_running:
                self.local_server.stop()
            self.local_server = LocalPreviewServer(folder)
            return {"success": True, "has_folder": True, "path": folder, "name": Path(folder).name, "terminal_cwd": folder}
        return {"success": False, "cancelled": True}

    def get_file_tree(self) -> List[Dict[str, Any]]:
        if not self.workspace.has_workspace:
            return []
        return self.workspace.get_file_tree()

    def read_file(self, rel_path: str) -> Dict[str, Any]:
        return self.workspace.read_file(rel_path)

    def write_file(self, rel_path: str, content: str) -> Dict[str, Any]:
        return self.workspace.write_file(rel_path, content)

    def compute_diff(self, rel_path: str, new_content: str) -> Dict[str, Any]:
        return self.workspace.compute_diff(rel_path, new_content)

    def fast_search(self, query: str) -> List[Dict[str, Any]]:
        return self.workspace.fast_search(query)

    def analyze_java_code(self, rel_path: Optional[str] = None) -> Dict[str, Any]:
        return self.workspace.analyze_java_code(rel_path)

    # Web Inspector & Local Server Methods
    def start_preview_server(self) -> Dict[str, Any]:
        url = self.local_server.start()
        return {"success": bool(url), "url": url}

    def crawl_website(self, url: str, max_pages: int = 3) -> Dict[str, Any]:
        return self.web_inspector.crawl_website(url, max_pages)

    # Goal & Workforce Methods
    def submit_goal(self, prompt: str) -> Dict[str, Any]:
        tree = self.workspace.get_file_tree(max_depth=2)
        summary = f"Root: {self.workspace.root_path.name}\nFiles: " + ", ".join([f["name"] for f in tree[:15]])
        return self.run_async(self.scheduler.submit_goal(prompt, summary))

    def approve_goal_plan(self, goal_id: str) -> bool:
        return self.run_async(self.scheduler.approve_and_start_goal(goal_id))

    def cancel_goal(self, goal_id: str) -> bool:
        return self.scheduler.cancel_goal(goal_id)

    def get_goals(self) -> List[Dict[str, Any]]:
        return list(self.scheduler.active_goals.values())

    # Approvals Gate
    def get_pending_approvals(self) -> List[Dict[str, Any]]:
        return self.approval_gate.get_pending()

    def approve_action(self, req_id: str) -> bool:
        return self.approval_gate.approve(req_id)

    def reject_action(self, req_id: str, reason: str = "Rejected by user") -> bool:
        return self.approval_gate.reject(req_id, reason)

    # Terminal
    def run_terminal_command(self, cmd: str) -> Dict[str, Any]:
        return self.run_async(self.terminal.execute_command(cmd))

    # Settings & Models
    def get_settings(self) -> Dict[str, Any]:
        return {
            "has_api_key": self.nvidia.is_configured(),
            "api_key_masked": (self.nvidia.api_key[:6] + "..." + self.nvidia.api_key[-4:]) if self.nvidia.is_configured() else "",
            "base_url": self.nvidia.base_url,
            "models": config.AVAILABLE_MODELS,
            "default_planner": config.DEFAULT_PLANNER_MODEL,
            "default_coder": config.DEFAULT_CODER_MODEL,
            "tokens_used": self.nvidia.total_tokens_used,
            "requests_made": self.nvidia.request_count
        }

    def save_settings(self, api_key: str, planner_model: str, coder_model: str) -> Dict[str, Any]:
        if api_key:
            self.nvidia.update_key(api_key)
            env_path = config.ROOT_DIR / ".env"
            try:
                with open(env_path, "w", encoding="utf-8") as f:
                    f.write(f"NVIDIA_API_KEY={api_key.strip()}\n")
                    f.write(f"NVIDIA_BASE_URL={config.NVIDIA_BASE_URL}\n")
                    f.write(f"DEFAULT_PLANNER_MODEL={planner_model}\n")
                    f.write(f"DEFAULT_CODER_MODEL={coder_model}\n")
            except Exception:
                pass

        test_res = self.nvidia.test_connection()
        return {"success": True, "connection_test": test_res}

    # Interactive Chat Agent
    def send_chat_message(
        self,
        message: str,
        active_file: Optional[str] = None,
        image_url: Optional[str] = None,
        crawl_url: Optional[str] = None
    ):
        """Asynchronously stream chat responses to UI using persistent background loop"""
        return self.run_async(self._run_chat(message, active_file, image_url, crawl_url))

    async def _run_chat(
        self,
        message: str,
        active_file: Optional[str] = None,
        image_url: Optional[str] = None,
        crawl_url: Optional[str] = None
    ):
        async for chunk in self.chat_agent.chat_stream(message, active_file, image_url, crawl_url):
            if self.window:
                js_code = f"if (window.onChatEvent) {{ window.onChatEvent({json.dumps(chunk)}); }}"
                try:
                    self.window.evaluate_js(js_code)
                except Exception:
                    pass

        # Signal done
        if self.window:
            try:
                self.window.evaluate_js("if (window.onChatEvent) { window.onChatEvent({type: 'done'}); }")
            except Exception:
                pass
        return {"success": True}

    def apply_chat_action(self, req_id: str) -> Dict[str, Any]:
        """Execute an approved action proposed during chat"""
        if req_id not in self.approval_gate.pending_approvals:
            return {"success": False, "error": "Action not found or already processed"}

        appr = self.approval_gate.pending_approvals[req_id]
        act_type = appr["action_type"]

        if act_type == "write_file":
            details = appr.get("details", {})
            path = details.get("path")
            content = details.get("new_content", "")
            write_res = self.workspace.write_file(path, content)
            self.approval_gate.approve(req_id)
            return {"success": write_res["success"], "message": f"Successfully updated {path}" if write_res["success"] else write_res.get("error")}

        elif act_type == "terminal_command":
            cmd = appr.get("details", {}).get("command", "")
            res = self.run_async(self.terminal.execute_command(cmd))
            self.approval_gate.approve(req_id)
            return {"success": res["success"], "stdout": res["stdout"], "stderr": res["stderr"], "message": f"Command executed: {cmd}"}

        return {"success": False, "error": "Unknown action type"}

    def reset_chat(self) -> bool:
        self.chat_agent.reset_chat()
        return True
