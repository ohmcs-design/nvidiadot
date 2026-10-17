"""
DOT AI - Native Desktop Application Entrypoint
Launches the Desktop Window using pywebview and binds Python engine to UI.
"""
import os
import sys
from pathlib import Path
import webview
from api_bridge import DesktopAPIBridge
import config

def main():
    # Ensure current directory is root
    os.chdir(config.ROOT_DIR)

    bridge = DesktopAPIBridge()
    html_file = (config.STATIC_DIR / "index.html").resolve()

    if not html_file.exists():
        print(f"Error: Could not find UI index file at {html_file}")
        sys.exit(1)

    print("==================================================")
    print("      DOT AI - Autonomous Code Editor (NVIDIA NIM)")
    print("==================================================")
    print(f"Workspace: {bridge.workspace.root_path}")
    print(f"NVIDIA API Key Status: {'Configured' if bridge.nvidia.is_configured() else 'Missing (Set in UI Settings)'}")
    print("Launching Desktop Application Window...")

    window = webview.create_window(
        title="DOT AI - Autonomous Code Editor [NVIDIA NIM]",
        url=str(html_file),
        js_api=bridge,
        width=1350,
        height=880,
        min_size=(960, 640),
        background_color="#0d1117"
    )

    bridge.set_window(window)
    webview.start(debug=False)

if __name__ == "__main__":
    main()
