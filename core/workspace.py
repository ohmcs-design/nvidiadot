"""
DOT AI - Workspace & File Manager
Handles folder trees, reading/writing files, diff generation, and native C fast-search.
"""
import os
import difflib
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
import config

IGNORED_PATTERNS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", 
    ".idea", ".vscode", "build", "dist", "target", ".DS_Store"
}

class WorkspaceManager:
    def __init__(self, root_dir: Optional[str] = None):
        self.root_path = Path(root_dir).resolve() if root_dir else None

    @property
    def has_workspace(self) -> bool:
        return self.root_path is not None and self.root_path.exists() and self.root_path.is_dir()

    def set_root(self, path_str: str) -> bool:
        if not path_str:
            self.root_path = None
            return True
        new_path = Path(path_str).resolve()
        if new_path.exists() and new_path.is_dir():
            self.root_path = new_path
            return True
        return False

    def get_file_tree(self, current_dir: Optional[Path] = None, depth: int = 0, max_depth: int = 2) -> List[Dict[str, Any]]:
        """Generate a hierarchical JSON tree of the workspace folder (optimized & non-blocking)"""
        if not self.has_workspace:
            return []

        if current_dir is None:
            current_dir = self.root_path

        if depth > max_depth:
            return []

        tree = []
        try:
            entries = []
            with os.scandir(current_dir) as it:
                for entry in it:
                    if entry.name in IGNORED_PATTERNS or entry.name.startswith("."):
                        continue
                    entries.append(entry)
                    if len(entries) >= 200:
                        break

            entries.sort(key=lambda e: (not e.is_dir(), e.name.lower()))
            for entry in entries:
                rel_path = str(Path(entry.path).relative_to(self.root_path)).replace("\\", "/")
                item = {
                    "name": entry.name,
                    "path": rel_path,
                    "is_dir": entry.is_dir(),
                }

                if entry.is_dir():
                    if depth < max_depth:
                        item["children"] = self.get_file_tree(Path(entry.path), depth + 1, max_depth)
                    else:
                        item["children"] = []
                else:
                    item["size"] = entry.stat().st_size
                    ext = Path(entry.name).suffix.lower()
                    item["ext"] = ext

                tree.append(item)
        except Exception as e:
            tree.append({"name": f"[Error: {str(e)}]", "path": "", "is_dir": False})

        return tree

    def read_file(self, rel_path: str) -> Dict[str, Any]:
        """Read file contents safely"""
        if not self.has_workspace:
            return {"success": False, "error": "No folder opened"}

        target = (self.root_path / rel_path).resolve()
        if not str(target).startswith(str(self.root_path)):
            return {"success": False, "error": "Access denied: Path outside workspace"}

        if not target.exists():
            return {"success": False, "error": "File does not exist"}

        try:
            with open(target, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            return {"success": True, "content": content, "path": rel_path}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def write_file(self, rel_path: str, new_content: str) -> Dict[str, Any]:
        """Write content to file (after approval)"""
        if not self.has_workspace:
            return {"success": False, "error": "No folder opened"}

        target = (self.root_path / rel_path).resolve()
        if not str(target).startswith(str(self.root_path)):
            return {"success": False, "error": "Access denied: Path outside workspace"}

        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            with open(target, "w", encoding="utf-8") as f:
                f.write(new_content)
            return {"success": True, "path": rel_path}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def compute_diff(self, rel_path: str, new_content: str) -> Dict[str, Any]:
        """Compute visual diff between existing file and proposed content"""
        read_res = self.read_file(rel_path)
        old_content = read_res["content"] if read_res["success"] else ""

        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)

        diff = "".join(difflib.unified_diff(
            old_lines, new_lines,
            fromfile=f"a/{rel_path}",
            tofile=f"b/{rel_path}"
        ))

        return {
            "path": rel_path,
            "old_content": old_content,
            "new_content": new_content,
            "unified_diff": diff,
            "has_changes": old_content != new_content,
            "is_new_file": not read_res["success"]
        }

    def fast_search(self, query: str) -> List[Dict[str, Any]]:
        """Run fast codebase search using compiled native C executable"""
        if not self.has_workspace:
            return []

        exe_name = "fast_search.exe" if os.name == "nt" else "fast_search_linux"
        exe_path = config.NATIVE_DIR / exe_name
        if not exe_path.exists() and os.name != "nt":
            exe_path = config.NATIVE_DIR / "fast_search"
        results = []

        if exe_path.exists():
            try:
                proc = subprocess.run(
                    [str(exe_path), str(self.root_path), query],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                for line in proc.stdout.splitlines():
                    parts = line.split(":", 2)
                    if len(parts) == 3:
                        file_abs, line_num, text = parts
                        rel = str(Path(file_abs).relative_to(self.root_path)).replace("\\", "/")
                        results.append({
                            "file": rel,
                            "line": int(line_num),
                            "text": text.strip()
                        })
                return results
            except Exception:
                pass

        # Python fallback search
        for root, dirs, files in os.walk(self.root_path):
            dirs[:] = [d for d in dirs if d not in IGNORED_PATTERNS and not d.startswith(".")]
            for file in files:
                filepath = Path(root) / file
                rel = str(filepath.relative_to(self.root_path)).replace("\\", "/")
                try:
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                        for idx, l in enumerate(f, 1):
                            if query.lower() in l.lower():
                                results.append({
                                    "file": rel,
                                    "line": idx,
                                    "text": l.strip()
                                })
                                if len(results) >= 100:
                                    return results
                except Exception:
                    continue
        return results

    def analyze_java_code(self, target_rel_path: Optional[str] = None) -> Dict[str, Any]:
        """Run native Java CodeAnalyzer to extract AST, classes, and methods"""
        if not self.has_workspace:
            return {"error": "No folder opened"}

        java_bin_dir = config.ROOT_DIR / "native_java"
        target_path = (self.root_path / target_rel_path).resolve() if target_rel_path else self.root_path

        try:
            cmd = ["java", "-cp", str(java_bin_dir), "dot.java.CodeAnalyzer", str(target_path)]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if proc.returncode == 0:
                import json
                return json.loads(proc.stdout)
            else:
                return {"error": proc.stderr or "Java analyzer execution failed"}
        except Exception as e:
            return {"error": str(e)}
