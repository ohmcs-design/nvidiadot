"""
DOT AI - Web & Docker Server
Serves the full DOT AI IDE as a modern web application accessible in any browser.
Ideal for Docker containers, remote servers, or running without local desktop GUI dependencies.
"""
import os
import sys
import json
import asyncio
import argparse
from pathlib import Path
from aiohttp import web

import config
from api_bridge import DesktopAPIBridge

class WebAppServer:
    def __init__(self, workspace_path: str = None):
        self.bridge = DesktopAPIBridge()
        self.clients = set()

        # Wire event listener from DesktopAPIBridge
        self.bridge.add_event_listener(self.on_bridge_event)

        # Auto-initialize workspace
        if workspace_path and Path(workspace_path).exists():
            self.bridge.pick_folder(target_folder=workspace_path)
        elif Path("/workspace").exists():
            self.bridge.pick_folder(target_folder="/workspace")

    def on_bridge_event(self, event_type: str, data: any):
        """Broadcast events to all connected SSE clients"""
        msg = f"data: {json.dumps({'event_type': event_type, 'data': data})}\n\n"
        dead_clients = set()
        for queue in self.clients:
            try:
                queue.put_nowait(msg)
            except Exception:
                dead_clients.add(queue)
        self.clients -= dead_clients

    async def handle_call(self, request):
        """Handle RPC calls from UI proxy"""
        try:
            body = await request.json()
        except Exception:
            return web.json_response({"error": "Invalid JSON"}, status=400)

        method_name = body.get("method")
        args = body.get("args", [])

        if not hasattr(self.bridge, method_name):
            return web.json_response({"error": f"Method {method_name} not found"}, status=404)

        method = getattr(self.bridge, method_name)
        try:
            if asyncio.iscoroutinefunction(method):
                res = await method(*args)
            else:
                loop = asyncio.get_event_loop()
                res = await loop.run_in_executor(None, method, *args)
            return web.json_response({"__dot_api_response": True, "result": res})
        except Exception as e:
            return web.json_response({"error": str(e), "__dot_api_response": True, "result": {"success": False, "error": str(e)}})

    async def handle_events(self, request):
        """Server-Sent Events (SSE) endpoint for real-time chat & workforce streaming"""
        response = web.StreamResponse(
            status=200,
            headers={
                "Content-Type": "text/event-stream",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*"
            }
        )
        await response.prepare(request)

        queue = asyncio.Queue()
        self.clients.add(queue)

        try:
            # Initial ping
            await response.write(b": connected\n\n")
            while True:
                msg = await queue.get()
                await response.write(msg.encode("utf-8"))
        except asyncio.CancelledError:
            pass
        finally:
            self.clients.discard(queue)

        return response

    async def handle_index(self, request):
        """Serve index.html at root"""
        index_file = config.STATIC_DIR / "index.html"
        return web.FileResponse(index_file)

    def create_app(self):
        app = web.Application()
        app.router.add_post("/api/call", self.handle_call)
        app.router.add_get("/api/events", self.handle_events)
        app.router.add_get("/", self.handle_index)
        app.router.add_static("/", path=str(config.STATIC_DIR))
        return app

def main():
    parser = argparse.ArgumentParser(description="DOT AI Web & Docker Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host address (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8080, help="Port to listen on (default: 8080)")
    parser.add_argument("--workspace", default=None, help="Workspace directory to open automatically")
    args = parser.parse_args()

    os.chdir(config.ROOT_DIR)

    server = WebAppServer(workspace_path=args.workspace)
    app = server.create_app()

    print("==================================================")
    print("      DOT AI - Autonomous Web & Docker IDE")
    print("==================================================")
    print(f"Server running at: http://{args.host}:{args.port}")
    if server.bridge.workspace.has_workspace:
        print(f"Active Workspace: {server.bridge.workspace.root_path}")
    else:
        print("Active Workspace: No folder opened (Use Open Folder in UI or mount /workspace)")
    print(f"NVIDIA API Key: {'Configured' if server.bridge.nvidia.is_configured() else 'Missing (Set in UI Settings)'}")
    print("==================================================")

    web.run_app(app, host=args.host, port=args.port)

if __name__ == "__main__":
    main()
