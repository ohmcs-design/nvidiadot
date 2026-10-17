"""
DOT AI - Approval Gatekeeper
Ensures no file modifications or destructive commands run without user authorization.
"""
import uuid
import time
import asyncio
from typing import Dict, Any, List, Optional, Callable

class ApprovalGate:
    def __init__(self):
        self.pending_approvals: Dict[str, Dict[str, Any]] = {}
        self.approval_futures: Dict[str, asyncio.Future] = {}

    def submit_request(
        self,
        goal_id: str,
        task_id: str,
        action_type: str,
        title: str,
        details: Dict[str, Any]
    ) -> str:
        """Register a pending approval request"""
        req_id = f"appr-{uuid.uuid4().hex[:8]}"
        self.pending_approvals[req_id] = {
            "id": req_id,
            "goal_id": goal_id,
            "task_id": task_id,
            "action_type": action_type,
            "title": title,
            "details": details,
            "status": "pending",
            "created_at": time.time()
        }
        return req_id

    async def wait_for_decision(self, req_id: str, timeout: float = 600.0) -> bool:
        """Wait asynchronously until user clicks Approve or Reject"""
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        self.approval_futures[req_id] = future

        try:
            decision = await asyncio.wait_for(future, timeout=timeout)
            return decision
        except asyncio.TimeoutError:
            self.reject(req_id, "Timed out waiting for user approval.")
            return False
        finally:
            self.approval_futures.pop(req_id, None)

    def approve(self, req_id: str) -> bool:
        if req_id in self.pending_approvals:
            self.pending_approvals[req_id]["status"] = "approved"
            self.pending_approvals[req_id]["resolved_at"] = time.time()
            if req_id in self.approval_futures and not self.approval_futures[req_id].done():
                future = self.approval_futures[req_id]
                future.get_loop().call_soon_threadsafe(future.set_result, True)
            return True
        return False

    def reject(self, req_id: str, reason: str = "Rejected by user") -> bool:
        if req_id in self.pending_approvals:
            self.pending_approvals[req_id]["status"] = "rejected"
            self.pending_approvals[req_id]["rejection_reason"] = reason
            self.pending_approvals[req_id]["resolved_at"] = time.time()
            if req_id in self.approval_futures and not self.approval_futures[req_id].done():
                future = self.approval_futures[req_id]
                future.get_loop().call_soon_threadsafe(future.set_result, False)
            return True
        return False

    def get_pending(self) -> List[Dict[str, Any]]:
        return [
            v for v in self.pending_approvals.values() 
            if v["status"] == "pending"
        ]
