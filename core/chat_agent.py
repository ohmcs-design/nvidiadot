"""
DOT AI - Conversational Chat & Action Agent
Allows users to chat casually, ask questions, inspect websites across multiple pages,
and command the AI to write code, edit files, and execute terminal commands.
Supports Vision-Language multimodal inspection via NVIDIA Nemotron 3.5 Super VL.
"""
import json
import re
from typing import Dict, Any, List, Optional, AsyncGenerator
from core.nvidia_client import NvidiaClient
from core.workspace import WorkspaceManager
from core.approval_gate import ApprovalGate
from core.terminal_runner import TerminalRunner
from core.web_inspector import WebInspector
import config

CHAT_AGENT_SYSTEM_PROMPT = """You are DOT AI, an elite autonomous AI code editor and software architect powered by NVIDIA Nemotron 3.5 Super VL.

CRITICAL RULES (STRICT SEPARATION OF TALKING AND CODING):
1. In your chat reply, ONLY TALK AND EXPLAIN CONCISELY (1-3 sentences max).
2. NEVER DUMP OR PRINT FULL CODE IN THE CHAT TEXT! Never print full CSS, HTML, JavaScript, Python, Java, or C in your normal message text!
3. Whenever you write, update, or create a file, place the code EXCLUSIVELY inside the ```action:write_file tag. The system will automatically turn this into a compact 1-click Approve Card for the user and apply it directly to their workspace.
4. If the user asks you to write code, your conversational text should just say what you did (e.g. "Maine style.css me modern project cards aur responsive hover styling likh di hai. Niche card se approve karein."). Never make the user copy-paste code!

CURRENT WORKSPACE:
{workspace_summary}

ACTIVE FILE IN EDITOR:
{active_file_context}

{web_inspection_context}

ACTION FORMATS:
1. To write or update a file:
```action:write_file
PATH: <relative_path>
EXPLANATION: <short 1-line reason>
CONTENT:
<complete new file content>
```

2. To execute a terminal command:
```action:run_command
COMMAND: <shell command, e.g., javac MyClass.java, gcc main.c, python test.py>
EXPLANATION: <short reason>
```

3. To browse or crawl a website:
```action:browse_website
URL: <url or http://127.0.0.1:8765/index.html>
MAX_PAGES: <number 1-5>
EXPLANATION: <short reason>
```
"""

class ChatAgent:
    def __init__(
        self,
        nvidia: NvidiaClient,
        workspace: WorkspaceManager,
        approval_gate: ApprovalGate,
        terminal: TerminalRunner,
        web_inspector: Optional[WebInspector] = None
    ):
        self.nvidia = nvidia
        self.workspace = workspace
        self.approval_gate = approval_gate
        self.terminal = terminal
        self.web_inspector = web_inspector or WebInspector()
        self.conversation_history: List[Dict[str, Any]] = []

    def reset_chat(self):
        self.conversation_history = []

    async def chat_stream(
        self,
        user_message: str,
        active_file_path: Optional[str] = None,
        image_url: Optional[str] = None,
        crawl_url: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream conversational response with thinking chunks, assistant talking text,
        and detected actions, strictly preventing code dumps into the chat text.
        """
        # Build workspace summary
        tree = self.workspace.get_file_tree(max_depth=2)
        tree_summary = ", ".join([f["name"] for f in tree[:20]]) or "Empty workspace"

        active_file_context = "None"
        if active_file_path:
            read_res = self.workspace.read_file(active_file_path)
            if read_res["success"]:
                active_file_context = f"{active_file_path} (length: {len(read_res['content'])} chars)\n```\n{read_res['content'][:2500]}\n```"

        # Check for URL crawling request
        web_context = ""
        url_match = re.search(r"https?://[^\s]+", user_message)
        target_crawl_url = crawl_url or (url_match.group(0) if url_match else None)

        if target_crawl_url:
            yield {"type": "web_status", "status": f"Crawling and inspecting website across multiple pages: {target_crawl_url}..."}
            crawl_data = self.web_inspector.crawl_website(target_crawl_url, max_pages=3)
            
            # Format report
            pages_summary = []
            for p in crawl_data.get("pages", []):
                if p.get("success"):
                    pages_summary.append(
                        f"Page: {p.get('url')} | Title: '{p.get('title')}'\n"
                        f"Headings: {', '.join(p.get('headings', [])[:5])}\n"
                        f"Snippet: {p.get('content_snippet', '')[:500]}\n"
                        f"Internal Links Discovered: {', '.join(p.get('internal_links', [])[:8])}"
                    )
                else:
                    pages_summary.append(f"Page: {p.get('url')} (Error: {p.get('error')})")

            web_context = "LIVE WEBSITE MULTI-PAGE ANALYSIS:\n" + "\n---\n".join(pages_summary)
            yield {"type": "web_status", "status": f"✓ Analyzed {len(crawl_data.get('pages', []))} pages from {target_crawl_url}."}

        system_msg = CHAT_AGENT_SYSTEM_PROMPT.format(
            workspace_summary=f"Folder: {self.workspace.root_path.name if self.workspace.root_path else 'None'}\nFiles: {tree_summary}",
            active_file_context=active_file_context,
            web_inspection_context=web_context
        )

        messages = [{"role": "system", "content": system_msg}]
        # Append up to last 10 turns of history
        for msg in self.conversation_history[-10:]:
            messages.append(msg)

        # Build user message with optional Vision image
        if image_url:
            user_content = [
                {"type": "text", "text": user_message},
                {"type": "image_url", "image_url": {"url": image_url}}
            ]
        else:
            user_content = user_message

        messages.append({"role": "user", "content": user_content})
        self.conversation_history.append({"role": "user", "content": user_message})

        full_content = []
        full_reasoning = []

        if not self.nvidia.is_configured():
            yield {
                "type": "content",
                "text": "NVIDIA API Key missing. Please click the green 'NVIDIA API' button in the top-right to set your key."
            }
            yield {"type": "done"}
            return

        # State tracking: strictly separate talking text from code actions
        in_action_block = False
        action_path_detected = None
        conversational_emitted = False
        accumulated_action_buffer = ""

        # Stream from NVIDIA Nemotron 3.5 Super VL
        async for chunk_type, text in self.nvidia.stream_chat(
            messages=messages,
            model=config.TARGET_NEMOTRON_MODEL,
            enable_thinking=config.ENABLE_THINKING
        ):
            if chunk_type == "reasoning":
                full_reasoning.append(text)
                yield {"type": "reasoning", "text": text}
            else:
                full_content.append(text)

                # Check if action or code block starts
                if not in_action_block:
                    current_full = "".join(full_content)
                    code_idx = current_full.find("```")
                    if code_idx != -1:
                        in_action_block = True
                        after_ticks = current_full[code_idx+3:].strip()
                        first_line = after_ticks.split("\n")[0].lower() if "\n" in after_ticks else after_ticks.lower()
                        status_msg = "Preparing file changes..."
                        if "write_file" in first_line:
                            status_msg = "Preparing file creation/update..."
                        elif "run_command" in first_line:
                            status_msg = "Preparing shell command..."
                        elif any(lang in first_line for lang in ["python", "py"]):
                            status_msg = "Creating Python script..."
                        elif any(lang in first_line for lang in ["html", "htm"]):
                            status_msg = "Creating HTML document..."
                        elif "css" in first_line:
                            status_msg = "Creating stylesheet..."
                        elif any(lang in first_line for lang in ["javascript", "js"]):
                            status_msg = "Creating JavaScript file..."
                        yield {"type": "action_in_progress", "status": status_msg}
                    else:
                        # Guard against trailing backticks so ``` is not leaked into conversational chat
                        if not (current_full.endswith("`") or current_full.endswith("``")):
                            conversational_emitted = True
                            yield {"type": "content", "text": text}
                else:
                    accumulated_action_buffer += text
                    if not action_path_detected:
                        path_match = re.search(r"PATH:\s*([^\r\n]+)", accumulated_action_buffer)
                        if path_match:
                            action_path_detected = path_match.group(1).strip()
                            yield {"type": "action_in_progress", "status": f"Creating/editing {action_path_detected}..."}
                        elif "action:run_command" in accumulated_action_buffer:
                            cmd_match = re.search(r"COMMAND:\s*([^\r\n]+)", accumulated_action_buffer)
                            if cmd_match:
                                yield {"type": "action_in_progress", "status": f"Preparing command: {cmd_match.group(1).strip()[:24]}..."}
                        else:
                            fn_match = re.search(r"[\w-]+\.(?:py|html|css|js|json|c|cpp|java|txt)", accumulated_action_buffer)
                            if fn_match:
                                action_path_detected = fn_match.group(0)
                                yield {"type": "action_in_progress", "status": f"Creating/editing {action_path_detected}..."}

        assistant_reply = "".join(full_content)
        self.conversation_history.append({"role": "assistant", "content": assistant_reply})

        # Parse proposed actions
        actions = self._extract_actions(assistant_reply, user_message=user_message, active_file_path=active_file_path)

        # If no conversational text was emitted before the action block, emit a clean message
        if in_action_block and not conversational_emitted:
            if action_path_detected:
                msg = f"Maine `{action_path_detected}` ka code taiyar kar diya hai. Niche diye gaye card se review ya approve karein."
            elif actions and actions[0].get("path"):
                msg = f"Maine `{actions[0]['path']}` ka code taiyar kar diya hai. Niche diye gaye card se review ya approve karein."
            else:
                msg = "Maine aapka code changes taiyar kar diya hai. Niche diye gaye card se review karein."
            yield {"type": "content", "text": msg}
        for act in actions:
            if act["type"] == "write_file":
                diff_info = self.workspace.compute_diff(act["path"], act["content"])
                req_id = self.approval_gate.submit_request(
                    goal_id="chat-session",
                    task_id=f"write-{act['path']}",
                    action_type="write_file",
                    title=f"Create/Update {act['path']}",
                    details=diff_info
                )
                yield {
                    "type": "action_proposal",
                    "action_id": req_id,
                    "action_type": "write_file",
                    "path": act["path"],
                    "explanation": act.get("explanation", ""),
                    "diff": diff_info.get("unified_diff", "")
                }
            elif act["type"] == "run_command":
                req_id = self.approval_gate.submit_request(
                    goal_id="chat-session",
                    task_id=f"cmd-{act['command'][:10]}",
                    action_type="terminal_command",
                    title=f"Run command: {act['command']}",
                    details={"command": act["command"], "explanation": act.get("explanation", "")}
                )
                yield {
                    "type": "action_proposal",
                    "action_id": req_id,
                    "action_type": "run_command",
                    "command": act["command"],
                    "explanation": act.get("explanation", "")
                }
            elif act["type"] == "browse_website":
                yield {
                    "type": "action_proposal",
                    "action_type": "browse_website",
                    "url": act["url"],
                    "explanation": act.get("explanation", "")
                }

        yield {"type": "done"}

    def _extract_actions(self, text: str, user_message: str = "", active_file_path: Optional[str] = None) -> List[Dict[str, Any]]:
        actions = []

        # 1. Match explicit write_file blocks
        write_blocks = re.findall(r"```action:write_file\s*\nPATH:\s*(.*?)\n(?:EXPLANATION:\s*(.*?)\n)?CONTENT:\s*\n(.*?)```", text, re.DOTALL)
        for path, expl, content in write_blocks:
            actions.append({
                "type": "write_file",
                "path": path.strip(),
                "explanation": expl.strip() if expl else "",
                "content": content
            })

        # 2. Match run_command blocks
        cmd_blocks = re.findall(r"```action:run_command\s*\nCOMMAND:\s*(.*?)\n(?:EXPLANATION:\s*(.*?)\n)?```", text, re.DOTALL)
        for cmd, expl in cmd_blocks:
            actions.append({
                "type": "run_command",
                "command": cmd.strip(),
                "explanation": expl.strip() if expl else ""
            })

        # 3. Match browse_website blocks
        browse_blocks = re.findall(r"```action:browse_website\s*\nURL:\s*(.*?)\n(?:MAX_PAGES:\s*(.*?)\n)?(?:EXPLANATION:\s*(.*?)\n)?```", text, re.DOTALL)
        for url, max_p, expl in browse_blocks:
            actions.append({
                "type": "browse_website",
                "url": url.strip(),
                "max_pages": int(max_p.strip()) if max_p and max_p.strip().isdigit() else 3,
                "explanation": expl.strip() if expl else ""
            })

        # 4. Fallback: If no action blocks were matched, but standard code blocks exist (e.g. ```python ... ```)
        if not actions:
            raw_blocks = re.findall(r"```([a-zA-Z0-9_-]*)\s*\n(.*?)```", text, re.DOTALL)
            for lang, code_content in raw_blocks:
                lang = lang.lower().strip()
                if lang.startswith("action:"):
                    continue
                inferred_path = None
                # Check first line of code for filename comment
                first_line = code_content.strip().split("\n")[0]
                fn_match = re.search(r"[\w-]+\.(?:py|html|css|js|jsx|ts|tsx|json|c|cpp|h|java|sql|sh|md|txt)", first_line)
                if fn_match:
                    inferred_path = fn_match.group(0)
                elif user_message:
                    fn_match_user = re.search(r"[\w-]+\.(?:py|html|css|js|jsx|ts|tsx|json|c|cpp|h|java|sql|sh|md|txt)", user_message)
                    if fn_match_user:
                        inferred_path = fn_match_user.group(0)

                if not inferred_path and active_file_path:
                    inferred_path = active_file_path

                if not inferred_path:
                    ext_map = {
                        "python": "script.py", "py": "script.py",
                        "html": "index.html", "htm": "index.html",
                        "css": "style.css",
                        "javascript": "app.js", "js": "app.js",
                        "json": "data.json",
                        "c": "main.c", "cpp": "main.cpp", "java": "Main.java",
                        "sh": "script.sh", "bash": "script.sh"
                    }
                    inferred_path = ext_map.get(lang, "code_file.txt")

                actions.append({
                    "type": "write_file",
                    "path": inferred_path,
                    "explanation": f"Generated {inferred_path} ({lang or 'code'})",
                    "content": code_content
                })

        return actions
