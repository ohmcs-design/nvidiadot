# DOT AI — Autonomous Code Editor [NVIDIA NIM Powered]

A folder-first, local-first AI Code Editor desktop application inspired by the **DOT AI Documentation Pack** and powered by **NVIDIA NIM** models.

---

## 🌟 Key Features

1. **Folder-Centric Workspace**:
   - Opens and watches any project folder on your PC.
   - Interactive file tree with language-specific icons (C, Python, Java, JS, JSON, etc.).
   - Switch folders anytime using the native Windows Folder Picker.

2. **Monaco Code Editor**:
   - Built on the core engine of **VS Code**.
   - Syntax highlighting, code folding, minimap, multi-tab editing.
   - Shortcut `Ctrl+S` to save files directly to disk.

3. **DOT AI Autonomous Workforce**:
   - **Multi-Goal Intake**: Concurrently plan and run up to 5 goals.
   - **Directed Acyclic Graph (DAG) Planner**: Breaks high-level goals into subtasks with dependency tracking.
   - **Specialized Workers**: Code Specialist (`mistralai/codestral-22b-v0.1`), Planner (`meta/llama-3.3-70b-instruct`), and Verifier (`nvidia/nemotron-4-340b-instruct`).

4. **Human-in-the-Loop Approval Gate**:
   - AI workers cannot modify files or execute terminal commands without your permission.
   - Integrated **Visual Diff Review Modal** shows proposed code changes before applying.

5. **Integrated Terminal & High-Performance C Grep**:
   - Native shell commands execution (compile with MinGW `gcc`, run with `python`, run test suites).
   - Compiled native C search executable (`native_c/fast_search.exe`) for fast code searches across thousands of files.

---

## 🚀 How to Launch

Double-click `run_editor.bat` or run:
```bash
python desktop_app.py
```

### Adding your NVIDIA API Key
1. Click the **NVIDIA API** button in the top right header.
2. Enter your key (starts with `nvapi-...`).
3. Click **Test Connection** and **Save Settings**.
   *(Your key is stored securely in your local `.env` file)*.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

