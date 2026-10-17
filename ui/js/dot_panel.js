/**
 * DOT AI - Autonomous Workforce UI Panel
 * Handles Goal Intake, Plan Approvals, Worker DAGs, and Diff Gates.
 */
class DotPanel {
  constructor() {
    this.goals = new Map();
    this.pendingApproval = null;
    this.initListeners();
  }

  initListeners() {
    // Goal Submit button
    document.getElementById("btn-submit-goal").onclick = () => this.submitGoal();
    document.getElementById("goal-input").onkeydown = (e) => {
      if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
        this.submitGoal();
      }
    };

    // Approval buttons
    document.getElementById("btn-view-diff").onclick = () => this.showDiffModal();
    document.getElementById("btn-approve-action").onclick = () => this.resolveAction(true);
    document.getElementById("btn-reject-action").onclick = () => this.resolveAction(false);

    // Diff modal buttons
    document.getElementById("btn-diff-approve").onclick = () => {
      document.getElementById("diff-modal").classList.remove("active");
      this.resolveAction(true);
    };
    document.getElementById("btn-diff-reject").onclick = () => {
      document.getElementById("diff-modal").classList.remove("active");
      this.resolveAction(false);
    };
    document.getElementById("btn-close-diff").onclick = () => {
      document.getElementById("diff-modal").classList.remove("active");
    };

    // Global event handler from Python backend
    window.onDotEvent = (event) => this.handleServerEvent(event);
  }

  async submitGoal() {
    const input = document.getElementById("goal-input");
    const prompt = input.value.trim();
    if (!prompt) return;

    input.value = "";
    const btn = document.getElementById("btn-submit-goal");
    btn.disabled = true;
    btn.innerText = "Planning with NVIDIA...";

    try {
      const res = await window.pywebview.api.submit_goal(prompt);
      if (res.success) {
        this.goals.set(res.goal.id, res.goal);
        this.renderGoals();
      } else {
        alert(res.error || "Failed to plan goal.");
      }
    } catch (e) {
      alert("Error submitting goal: " + e);
    } finally {
      btn.disabled = false;
      btn.innerHTML = "<span>+ Plan Goal</span>";
    }
  }

  handleServerEvent(event) {
    const type = event.type;
    const data = event.data;

    if (type === "goal_created" || type === "goal_updated") {
      this.goals.set(data.id, data);
      this.renderGoals();
    } else if (type === "task_updated") {
      const goal = this.goals.get(data.goal_id);
      if (goal && goal.plan && goal.plan.subtasks) {
        const subtasks = goal.plan.subtasks;
        const idx = subtasks.findIndex(t => t.id === data.task.id);
        if (idx !== -1) {
          subtasks[idx] = data.task;
        }
        this.renderGoals();
      }
    } else if (type === "goal_log") {
      const goal = this.goals.get(data.goal_id);
      if (goal) {
        if (!goal.logs) goal.logs = [];
        goal.logs.push(data.log);
        this.renderGoals();
      }
    }

    this.checkPendingApprovals();
  }

  async checkPendingApprovals() {
    if (!window.pywebview || !window.pywebview.api) return;
    const pending = await window.pywebview.api.get_pending_approvals();
    const banner = document.getElementById("approval-center");
    const title = document.getElementById("approval-title");

    if (pending && pending.length > 0) {
      this.pendingApproval = pending[0];
      title.innerText = this.pendingApproval.title;
      banner.style.display = "block";
    } else {
      this.pendingApproval = null;
      banner.style.display = "none";
    }
  }

  showDiffModal() {
    if (!this.pendingApproval) return;
    const modal = document.getElementById("diff-modal");
    const diffText = document.getElementById("diff-text");
    const title = document.getElementById("diff-modal-title");

    title.innerText = `Review Changes: ${this.pendingApproval.title}`;
    const details = this.pendingApproval.details || {};
    diffText.innerText = details.unified_diff || JSON.stringify(details, null, 2);
    modal.classList.add("active");
  }

  async resolveAction(approve) {
    if (!this.pendingApproval) return;
    const reqId = this.pendingApproval.id;

    if (approve) {
      await window.pywebview.api.approve_action(reqId);
    } else {
      await window.pywebview.api.reject_action(reqId, "User rejected via UI");
    }

    this.pendingApproval = null;
    document.getElementById("approval-center").style.display = "none";
  }

  async approveGoalPlan(goalId) {
    const res = await window.pywebview.api.approve_goal_plan(goalId);
    if (!res) {
      alert("Could not start goal.");
    }
  }

  async cancelGoal(goalId) {
    await window.pywebview.api.cancel_goal(goalId);
  }

  renderGoals() {
    const container = document.getElementById("goals-container");
    const counter = document.getElementById("active-goal-counter");
    container.innerHTML = "";

    const goalList = Array.from(this.goals.values());
    counter.innerText = `${goalList.filter(g => g.status === 'running').length} / 5 Running`;

    if (goalList.length === 0) {
      container.innerHTML = `
        <div style="text-align:center; padding:30px 10px; color:var(--text-muted); font-size:12px;">
          No active goals.<br>Submit a coding goal above to dispatch autonomous workers.
        </div>
      `;
      return;
    }

    goalList.forEach(goal => {
      const card = document.createElement("div");
      card.className = `goal-card ${goal.status}`;

      const subtasks = (goal.plan && goal.plan.subtasks) || [];
      const subtaskHtml = subtasks.map(t => `
        <div class="subtask-item ${t.status === 'completed' ? 'completed' : ''}">
          <span>${t.status === 'completed' ? '✓' : (t.status === 'running' ? '⏳' : '○')} ${t.title}</span>
          <span style="font-size:10px; opacity:0.7;">[${t.worker_type}]</span>
        </div>
      `).join("");

      let actionButtons = "";
      if (goal.status === "awaiting_approval") {
        actionButtons = `
          <div style="margin-top:10px; display:flex; gap:8px;">
            <button class="btn btn-accent btn-approve-plan" style="flex:1;">Approve & Start</button>
            <button class="btn btn-cancel-plan" style="color:var(--danger);">Reject</button>
          </div>
        `;
      } else if (goal.status === "running") {
        actionButtons = `
          <div style="margin-top:10px;">
            <button class="btn btn-cancel-plan" style="width:100%; font-size:11px; color:var(--danger);">Stop Workflow</button>
          </div>
        `;
      }

      card.innerHTML = `
        <div class="goal-title">
          <span>${goal.title}</span>
          <span class="status-pill status-${goal.status}">${goal.status.replace('_', ' ')}</span>
        </div>
        <div style="font-size:11px; color:var(--text-muted);">${(goal.plan && goal.plan.summary) || ''}</div>
        <div class="progress-track">
          <div class="progress-fill" style="width: ${goal.progress || 0}%"></div>
        </div>
        <div class="subtask-tree">${subtaskHtml}</div>
        ${actionButtons}
      `;

      const approveBtn = card.querySelector(".btn-approve-plan");
      if (approveBtn) approveBtn.onclick = () => this.approveGoalPlan(goal.id);

      const cancelBtn = card.querySelector(".btn-cancel-plan");
      if (cancelBtn) cancelBtn.onclick = () => this.cancelGoal(goal.id);

      container.appendChild(card);
    });
  }
}

window.dotPanel = new DotPanel();
