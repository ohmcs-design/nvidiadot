"""
DOT AI - Terminal & Command Runner
Executes shell commands (GCC compiler, Python tests, Linters) inside the workspace.
"""
import os
import asyncio
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, AsyncGenerator

class TerminalRunner:
    def __init__(self, cwd: Path):
        self.cwd = Path(cwd)

    def set_cwd(self, new_cwd: Path):
        self.cwd = Path(new_cwd)

    async def execute_command(self, cmd_str: str, timeout: int = 60) -> Dict[str, Any]:
        """Execute command asynchronously and return results"""
        stripped = cmd_str.strip()

        stripped_lower = stripped.lower()

        # Handle drive switch e.g. 'd:' or 'c:'
        if len(stripped) == 2 and stripped[1] == ':' and stripped[0].isalpha():
            drive_path = Path(f"{stripped.upper()}\\")
            if drive_path.exists():
                self.cwd = drive_path.resolve()
                return {
                    "command": cmd_str,
                    "exit_code": 0,
                    "stdout": f"{self.cwd}\n",
                    "stderr": "",
                    "success": True,
                    "cwd": str(self.cwd)
                }

        # Handle 'cls' or 'clear'
        if stripped_lower in ("cls", "clear"):
            return {
                "command": cmd_str,
                "exit_code": 0,
                "stdout": "",
                "stderr": "",
                "success": True,
                "clear": True,
                "cwd": str(self.cwd)
            }

        # Handle 'cd' command directly to persist directory changes
        if stripped_lower == "cd" or stripped_lower.startswith("cd ") or stripped_lower.startswith("cd\\") or stripped_lower.startswith("cd/"):
            raw_target = stripped[2:].strip()
            # Remove /d flag if present in Windows cmd style: cd /d D:\path
            if raw_target.lower().startswith("/d "):
                raw_target = raw_target[3:].strip()
            target = raw_target.strip('"').strip("'").strip()

            if not target:
                return {
                    "command": cmd_str,
                    "exit_code": 0,
                    "stdout": str(self.cwd) + "\n",
                    "stderr": "",
                    "success": True,
                    "cwd": str(self.cwd)
                }

            target_path = Path(target)
            if not target_path.is_absolute():
                new_path = (self.cwd / target_path).resolve()
            else:
                new_path = target_path.resolve()

            if new_path.exists() and new_path.is_dir():
                self.cwd = new_path
                return {
                    "command": cmd_str,
                    "exit_code": 0,
                    "stdout": f"{self.cwd}\n",
                    "stderr": "",
                    "success": True,
                    "cwd": str(self.cwd)
                }
            else:
                return {
                    "command": cmd_str,
                    "exit_code": 1,
                    "stdout": "",
                    "stderr": f"The system cannot find the path specified: {target}\n",
                    "success": False,
                    "cwd": str(self.cwd)
                }

        try:
            proc = await asyncio.create_subprocess_exec(
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy", "Bypass",
                "-Command", cmd_str,
                cwd=str(self.cwd),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout_bytes, stderr_bytes = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            
            stdout_text = stdout_bytes.decode("utf-8", errors="replace")
            stderr_text = stderr_bytes.decode("utf-8", errors="replace")
            
            return {
                "command": cmd_str,
                "exit_code": proc.returncode,
                "stdout": stdout_text,
                "stderr": stderr_text,
                "success": proc.returncode == 0,
                "cwd": str(self.cwd)
            }
        except asyncio.TimeoutError:
            return {
                "command": cmd_str,
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Command timed out after {timeout} seconds.",
                "success": False,
                "cwd": str(self.cwd)
            }
        except Exception as e:
            return {
                "command": cmd_str,
                "exit_code": -1,
                "stdout": "",
                "stderr": str(e),
                "success": False,
                "cwd": str(self.cwd)
            }
