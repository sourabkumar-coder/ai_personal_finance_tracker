/**
 * AI Personal Finance Tracker - Frontend Application Engine
 * Connects to FastAPI backend, manages state, renders glassmorphic components,
 * and handles live 4-second polling for automatic UPI transaction detection.
 */

// Configuration
const API_BASE = "https://ai-personal-finance-tracker-7qp8.onrender.com";


// Auth variables
let authToken = localStorage.getItem('authToken') || null;

async function apiFetch(endpoint, options = {}) {
  const headers = { ...options.headers };
  if (authToken) {
    headers['Authorization'] = Bearer ;
  }
  const config = { ...options, headers };
  
  // if endpoint is absolute url, don't prepend API_BASE
  const url = endpoint.startsWith('http') ? endpoint : ${API_BASE};
  
  const res = await fetch(url, config);
  if (res.status === 401) {
    // Show login modal
    authToken = null;
    localStorage.removeItem('authToken');
    openStudentModal(); // Assuming we reuse the student modal for Auth
    showToast('Session Expired', 'Please login again.', 'error');
  }
  return res;
}

// Global State
let currentStudentId = parseInt(localStorage.getItem("activeStudentId")) || 0;
let currentStudent = null;
let currentCurrency = "INR";
let currencySymbol = "₹";
let previousExpenseCount = 0;
let pollingInterval = null;
let authToken = localStorage.getItem("authToken") || null;

async function apiFetch(endpoint, options = {}) {
  const headers = { ...options.headers };
  if (authToken) {
    headers["Authorization"] = `Bearer ${authToken}`;
  }
  const config = { ...options, headers };
  
  const url = endpoint.startsWith("http") ? endpoint : `${API_BASE}${endpoint}`;
  
  const res = await fetch(url, config);
  if (res.status === 401) {
    authToken = null;
    localStorage.removeItem("authToken");
    openStudentModal();
    showToast("Session Expired", "Please login again.", "error");
  }
  return res;
}

// Initialize when DOM is ready
document.addEventListener("DOMContentLoaded", () => {
  initApp();
  setupPolling();
});

/**
 * Initialize application state, students, and dashboard data.
 */
async function initApp() {
  if (!authToken) {
    openStudentModal();
    return;
  }
  try {
    const meRes = await apiFetch("/api/auth/me");
    if (meRes.ok) {
      currentStudent = await meRes.json();
      currentStudentId = currentStudent.id;
      localStorage.setItem("activeStudentId", currentStudentId);
      currentCurrency = currentStudent.currency || "INR";
      currencySymbol = currentCurrency === "INR" ? "₹" : "$";
      updateSidebarProfile();
      loadAllViews();
    } else {
      authToken = null;
      localStorage.removeItem("authToken");
      openStudentModal();
    }
  } catch (err) {
    console.warn("Backend not reached:", err);
    showToast("Connection Error", "Could not connect to backend to load student data.", "error");
  }
}

/**
 * Setup 4-second live polling for auto-detected transactions.
 */
function setupPolling() {
  if (pollingInterval) clearInterval(pollingInterval);
  pollingInterval = setInterval(async () => {
    if (!currentStudentId || currentStudentId <= 0) return;
    await checkNewTransactions();
  }, 4000);
}

/**
 * Check if Android or simulator pushed a new transaction.
 */
async function checkNewTransactions() {
  if (!currentStudentId || currentStudentId <= 0) return;
  
  try {
    const res = await fetch(`${API_BASE}/api/expenses/${currentStudentId}`);
    if (!res.ok) return;
    const expenses = await res.json();

    if (previousExpenseCount > 0 && expenses.length > previousExpenseCount) {
      const newest = expenses[0]; // Newest first
      if (newest && newest.is_automatically_detected) {
        showToast(
          "New Transaction Auto-Detected!",
          `${currencySymbol}${newest.amount.toFixed(2)} at ${newest.merchant || newest.title} categorized as ${newest.category}`,
          "success"
        );
        // Refresh overview and tracking status
        loadOverview();
        loadTrackingStatus();
        loadBudgetAlerts();
        loadRecommendations();
        if (document.getElementById("tab-expenses").classList.contains("active")) {
          loadExpenses();
        }
        if (document.getElementById("tab-budgets").classList.contains("active")) {
          loadBudgets();
        }
      }
    }
    previousExpenseCount = expenses.length;
  } catch (err) {
    // Silent fail on background poll
  }
}

/**
 * Load all views for the active student.
 */
function loadAllViews() {
  loadBudgetAlerts();
  loadOverview();
  loadTrackingStatus();
  loadExpenses();
  loadBudgets();
  loadGoals();
  loadRecommendations();
  loadTrackingSettings();
}

/**
 * Load & Render Active Budget Exceeded / Warning Banners
 */
async function loadBudgetAlerts() {
  if (!currentStudentId || currentStudentId <= 0) return;
  const banner = document.getElementById("budget-alert-banner");
  if (!banner) return;

  try {
    const res = await fetch(`${API_BASE}/api/budgets/${currentStudentId}/alerts`);
    if (!res.ok) {
      banner.style.display = "none";
      return;
    }
    const alerts = await res.json();

    if (!alerts || alerts.length === 0) {
      banner.style.display = "none";
      banner.innerHTML = "";
      return;
    }

    const firstExceeded = alerts.find((a) => a.is_exceeded) || alerts[0];
    const className = firstExceeded.is_exceeded ? "alert-banner-exceeded" : "alert-banner-warning";
    const alertTitle = firstExceeded.is_exceeded
      ? `Budget Limit Exceeded in ${escapeHtml(firstExceeded.category)}!`
      : `Approaching Budget Limit in ${escapeHtml(firstExceeded.category)}`;

    banner.className = className;
    banner.style.display = "flex";
    banner.innerHTML = `
      <div style="display: flex; align-items: center; gap: 0.85rem;">
        <div>
          <h4 style="margin: 0; font-size: 0.98rem; font-weight: 700; color: var(--text-main);">${alertTitle}</h4>
          <p style="margin: 0.2rem 0 0 0; font-size: 0.82rem; color: var(--text-muted);">${escapeHtml(firstExceeded.message)}</p>
        </div>
      </div>
      <button class="btn btn-secondary btn-sm" style="flex-shrink: 0;" onclick="switchTab('budgets')">View Budgets</button>
    `;
  } catch (e) {
    console.error("Error loading budget alerts:", e);
    banner.style.display = "none";
  }
}

/**
 * Handle Real-Time Budget Alert Notification Trigger
 */
function checkAndShowBudgetAlert(budgetAlert) {
  if (!budgetAlert) return;

  const isExceeded = budgetAlert.is_exceeded;
  const isWarning = budgetAlert.is_warning;
  if (!isExceeded && !isWarning) return;

  const title = isExceeded ? "BUDGET EXCEEDED ALERT!" : "Budget Warning";
  const toastType = isExceeded ? "error" : "info";

  // Trigger Toast Notification
  showToast(title, budgetAlert.message, toastType);

  // Trigger Native Desktop Notification if granted
  if ("Notification" in window && Notification.permission === "granted") {
    try {
      new Notification(title, {
        body: budgetAlert.message,
        tag: `budget-alert-${budgetAlert.category}`,
      });
    } catch (e) {
      console.warn("Desktop notification trigger error:", e);
    }
  }

  loadBudgetAlerts();
  loadRecommendations();
  loadBudgets();
}

/**
 * Switch Active Dashboard Tab
 */
function switchTab(tabId) {
  document.querySelectorAll(".tab-view").forEach((tab) => tab.classList.remove("active"));
  document.querySelectorAll(".nav-links button").forEach((btn) => btn.classList.remove("active"));

  const targetTab = document.getElementById(`tab-${tabId}`);
  const targetBtn = document.getElementById(`nav-btn-${tabId}`);
  if (targetTab) targetTab.classList.add("active");
  if (targetBtn) targetBtn.classList.add("active");

  const headingMap = {
    overview: "Financial Overview",
    "ai-advisor": "Gemini AI Financial Advisor",
    expenses: "Itemized Expenses",
    budgets: "Monthly Budgets",
    goals: "Financial Savings Goals",
    "auto-tracking": "Automatic UPI & Bank Detection",
  };
  const topHeading = document.getElementById("top-page-heading");
  if (topHeading) topHeading.textContent = headingMap[tabId] || "Financial Overview";

  // Reload tab-specific data
  if (tabId === "overview") loadOverview();
  if (tabId === "expenses") loadExpenses();
  if (tabId === "budgets") loadBudgets();
  if (tabId === "goals") loadGoals();
  if (tabId === "ai-advisor") loadRecommendations();
  if (tabId === "auto-tracking") {
    loadTrackingStatus();
    loadTrackingSettings();
  }
}

/**
 * Load Overview Tab (Metrics, Auto-Tracking Card, Recent Transactions)
 */
async function loadOverview() {
  if (!currentStudentId || currentStudentId <= 0) {
    console.warn("Cannot load overview: Invalid student ID");
    return;
  }

  try {
    // 1. Student Profile
    const profRes = await fetch(`${API_BASE}/api/onboarding/profile/${currentStudentId}`);
    if (profRes.ok) {
      currentStudent = await profRes.json();
      currentCurrency = currentStudent.currency || "INR";
      currencySymbol = currentCurrency === "INR" ? "₹" : "$";
      updateSidebarProfile();
    }

    // 2. Analytics Overview
    const analyticsRes = await fetch(`${API_BASE}/api/analytics/${currentStudentId}/overview`);
    if (analyticsRes.ok) {
      const a = await analyticsRes.json();
      const allowance = a.monthly_allowance || 0.0;
      const spent = a.total_spent || 0.0;
      const remaining = a.remaining_balance || 0.0;
      const pct = allowance > 0 ? ((spent / allowance) * 100).toFixed(1) : 0;

      const elAllowance = document.getElementById("val-monthly-allowance");
      if (elAllowance) elAllowance.textContent = `${currencySymbol}${allowance.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;

      const elCurrency = document.getElementById("val-monthly-currency");
      if (elCurrency) elCurrency.textContent = `${currentCurrency} / Month`;

      const elSpent = document.getElementById("val-total-spent");
      if (elSpent) elSpent.textContent = `${currencySymbol}${spent.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;

      const elSpentPct = document.getElementById("val-spent-pct");
      if (elSpentPct) elSpentPct.textContent = `${pct}% of monthly allowance`;

      const elRemaining = document.getElementById("val-remaining-balance");
      if (elRemaining) elRemaining.textContent = `${currencySymbol}${remaining.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;

      const daysInMonth = 30;
      const day = new Date().getDate();
      const daysLeft = Math.max(1, daysInMonth - day);
      const safeDaily = remaining > 0 ? (remaining / daysLeft).toFixed(2) : "0.00";
      const elDaily = document.getElementById("val-daily-budget");
      if (elDaily) elDaily.textContent = `Safe daily spend: ${currencySymbol}${safeDaily}`;
    }

    // 2b. Category Breakdown
    const catRes = await fetch(`${API_BASE}/api/analytics/${currentStudentId}/by-category`);
    if (catRes.ok) {
      const catData = await catRes.json();
      renderCategoryList(catData);
    }

    // 3. Forecast
    const fcRes = await fetch(`${API_BASE}/api/recommendations/${currentStudentId}/forecast`);
    if (fcRes.ok) {
      const fc = await fcRes.json();
      const statusEl = document.getElementById("val-health-status");
      if (statusEl) {
        statusEl.textContent = fc.health_status || "Healthy";
        statusEl.style.color = fc.health_status === "Critical" ? "var(--accent-rose)" : fc.health_status === "Warning" ? "var(--accent-amber)" : "var(--accent-emerald)";
      }
      const burnEl = document.getElementById("val-projected-burn");
      if (burnEl) {
        burnEl.textContent = `Forecast: ${currencySymbol}${(fc.projected_month_end_spent || 0).toFixed(0)} spent`;
      }
    }

    // 4. Recent Expenses
    const expRes = await fetch(`${API_BASE}/api/expenses/${currentStudentId}`);
    if (expRes.ok) {
      const expenses = await expRes.json();
      previousExpenseCount = expenses.length;
      renderRecentTable(expenses.slice(0, 7));
    }
  } catch (err) {
    console.error("Error loading overview:", err);
  }
}

/**
 * Render Category Spend List in Overview
 */
function renderCategoryList(catSpend) {
  const container = document.getElementById("overview-category-list");
  const countBadge = document.getElementById("overview-total-categories");
  if (!container) return;

  let entries = [];
  if (Array.isArray(catSpend)) {
    entries = catSpend.map((item) => [item.category, item.amount]);
  } else if (typeof catSpend === "object" && catSpend !== null) {
    entries = Object.entries(catSpend);
  }

  if (countBadge) countBadge.textContent = `${entries.length} Categories`;

  if (entries.length === 0) {
    container.innerHTML = `<p style="color: var(--text-muted); font-size: 0.85rem;">No category expenses recorded yet.</p>`;
    return;
  }

  const maxVal = Math.max(...entries.map(([, v]) => v), 1);
  container.innerHTML = entries
    .map(([cat, val]) => {
      const pct = Math.min(100, Math.round((val / maxVal) * 100));
      return `
        <div>
          <div style="display: flex; justify-content: space-between; font-size: 0.84rem; margin-bottom: 0.25rem;">
            <span>${escapeHtml(cat)}</span>
            <span style="font-weight: 600;">${currencySymbol}${val.toFixed(2)}</span>
          </div>
          <div style="width: 100%; height: 6px; background: rgba(255,255,255,0.08); border-radius: 3px; overflow: hidden;">
            <div style="width: ${pct}%; height: 100%; background: var(--primary); border-radius: 3px;"></div>
          </div>
        </div>
      `;
    })
    .join("");
}

/**
 * Edit Monthly Allowance Modal Functions
 */
function openEditAllowanceModal() {
  if (!currentStudent) return;
  const inputAmt = document.getElementById("edit-allowance-amount");
  const inputCurr = document.getElementById("edit-allowance-currency");
  if (inputAmt) inputAmt.value = currentStudent.monthly_allowance || 0;
  if (inputCurr) inputCurr.value = currentStudent.currency || "INR";
  openModal("modal-edit-allowance");
}

async function handleUpdateAllowance(e) {
  e.preventDefault();
  if (!currentStudentId || currentStudentId <= 0) return;

  const allowance = parseFloat(document.getElementById("edit-allowance-amount").value);
  const currency = document.getElementById("edit-allowance-currency").value;

  try {
    const res = await fetch(`${API_BASE}/api/onboarding/profile/${currentStudentId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        monthly_allowance: allowance,
        currency: currency,
      }),
    });

    if (res.ok) {
      currentStudent = await res.json();
      currentCurrency = currentStudent.currency || "INR";
      currencySymbol = currentCurrency === "INR" ? "₹" : "$";
      showToast("Allowance Updated", `Monthly allowance set to ${currencySymbol}${allowance.toFixed(2)}.`, "success");
      closeModal("modal-edit-allowance");
      updateSidebarProfile();
      loadOverview();
      loadBudgets();
    } else {
      showToast("Error", "Could not update monthly allowance.", "error");
    }
  } catch (err) {
    showToast("Error", "Network error updating allowance.", "error");
  }
}

/**
 * Render Recent Transactions Table
 */
function renderRecentTable(expenses) {
  const tbody = document.getElementById("overview-recent-tbody");
  if (!tbody) return;

  if (!expenses || expenses.length === 0) {
    tbody.innerHTML = `<tr><td colspan="3" style="text-align: center; color: var(--text-muted);">No expenses logged yet.</td></tr>`;
    return;
  }

  tbody.innerHTML = expenses
    .map((e) => {
      const autoBadge = e.is_automatically_detected
        ? `<span class="badge-auto-detected" title="${e.notes || ''}">Auto • ${e.source_app || 'UPI'}</span>`
        : "";
      return `
        <tr>
          <td>
            <div style="font-weight: 500;">${escapeHtml(e.title || e.merchant || 'Expense')}</div>
            ${autoBadge}
          </td>
          <td><span class="tag-badge">${escapeHtml(e.category)}</span></td>
          <td style="font-weight: 600; color: var(--text-main);">${currencySymbol}${e.amount.toFixed(2)}</td>
        </tr>
      `;
    })
    .join("");
}

/**
 * Load Tracking Status (Overview banner & Auto-Tracking Tab)
 */
async function loadTrackingStatus() {
  if (!currentStudentId || currentStudentId <= 0) {
    console.warn("Cannot load tracking status: Invalid student ID");
    return;
  }
  try {
    const res = await fetch(`${API_BASE}/api/transactions/${currentStudentId}/status`);
    if (!res.ok) return;
    const stat = await res.json();

    const lastDetectedVal = document.getElementById("tracking-last-detected-val");
    if (lastDetectedVal) {
      if (stat.last_detected_at && stat.last_merchant) {
        const timeAgo = formatTimeAgo(new Date(stat.last_detected_at));
        lastDetectedVal.textContent = `${stat.last_merchant} (${currencySymbol}${stat.last_amount}) • ${timeAgo}`;
      } else {
        lastDetectedVal.textContent = "Monitoring UPI apps...";
      }
    }

    const pill = document.getElementById("tracking-status-pill");
    if (pill) {
      pill.textContent = stat.auto_tracking_enabled ? "● Active" : "○ Paused";
      pill.style.color = stat.auto_tracking_enabled ? "#34d399" : "#94a3b8";
    }

    const pillLg = document.getElementById("auto-tracking-pill-lg");
    if (pillLg) {
      pillLg.textContent = stat.auto_tracking_enabled ? `● Active • ${stat.total_auto_detected} detected` : "○ Paused";
    }
  } catch (err) {
    console.warn("Could not fetch tracking status:", err);
  }
}

/**
 * Load Auto-Tracking Settings
 */
async function loadTrackingSettings() {
  if (!currentStudentId || currentStudentId <= 0) {
    console.warn("Cannot load tracking settings: Invalid student ID");
    return;
  }
  try {
    const res = await fetch(`${API_BASE}/api/transactions/${currentStudentId}/settings`);
    if (!res.ok) return;
    const s = await res.json();

    const tTrack = document.getElementById("toggle-auto-tracking");
    const tCat = document.getElementById("toggle-auto-categorize");
    const tConf = document.getElementById("toggle-require-confirm");

    if (tTrack) tTrack.checked = s.auto_tracking_enabled;
    if (tCat) tCat.checked = s.auto_categorize_enabled;
    if (tConf) tConf.checked = s.require_confirmation_low_confidence;
  } catch (err) {
    console.warn("Could not fetch settings:", err);
  }
}

/**
 * Handle Settings Toggle Update
 */
async function handleToggleSetting(key, val) {
  if (!currentStudentId || currentStudentId <= 0) {
    showToast("No Student Selected", "Please select a valid student profile first.", "error");
    return;
  }
  try {
    const payload = {};
    payload[key] = val;
    const res = await fetch(`${API_BASE}/api/transactions/${currentStudentId}/settings`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (res.ok) {
      showToast("Settings Updated", "Your tracking preference has been synchronized.", "success");
      loadTrackingStatus();
    }
  } catch (err) {
    showToast("Update Failed", "Could not save setting changes.", "error");
  }
}

/**
 * Load Full Expenses Table
 */
async function loadExpenses() {
  if (!currentStudentId || currentStudentId <= 0) {
    console.warn("Cannot load expenses: Invalid student ID");
    return;
  }
  const tbody = document.getElementById("expenses-table-tbody");
  if (!tbody) return;

  const catFilter = document.getElementById("filter-expense-category")?.value || "";
  let url = `${API_BASE}/api/expenses/${currentStudentId}`;
  if (catFilter) url += `?category=${encodeURIComponent(catFilter)}`;

  try {
    const res = await apiFetch(url);
    if (!res.ok) return;
    const expenses = await res.json();

    if (expenses.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-muted);">No expense entries found.</td></tr>`;
      return;
    }

    tbody.innerHTML = expenses
      .map((e) => {
        const autoBadge = e.is_automatically_detected
          ? `<span class="badge-auto-detected">Auto • ${e.source_app || 'UPI'}</span>`
          : `<span style="font-size: 0.75rem; color: var(--text-dim);">${escapeHtml(e.payment_method || 'Manual')}</span>`;

        return `
          <tr>
            <td style="font-size: 0.85rem; color: var(--text-muted);">${e.date}</td>
            <td>
              <div style="font-weight: 500;">${escapeHtml(e.title || e.merchant || 'Expense')}</div>
              ${e.subcategory ? `<span style="font-size: 0.72rem; color: var(--text-dim);">${escapeHtml(e.subcategory)}</span>` : ''}
            </td>
            <td><span class="tag-badge">${escapeHtml(e.category)}</span></td>
            <td>${autoBadge}</td>
            <td style="font-size: 0.82rem; color: var(--text-muted);">${escapeHtml(e.notes || '-')}</td>
            <td style="font-weight: 600; color: var(--text-main);">${currencySymbol}${e.amount.toFixed(2)}</td>
            <td>
              <button class="btn btn-secondary btn-sm" style="padding: 0.2rem 0.5rem; color: var(--accent-rose);" onclick="handleDeleteExpense(${e.id})">Delete</button>
            </td>
          </tr>
        `;
      })
      .join("");
  } catch (err) {
    console.error("Error loading expenses:", err);
  }
}

/**
 * Handle Delete Expense
 */
async function handleDeleteExpense(expenseId) {
  if (!currentStudentId || currentStudentId <= 0) {
    showToast("No Student Selected", "Please select a valid student profile first.", "error");
    return;
  }
  
  if (!confirm("Are you sure you want to delete this expense?")) return;
  try {
    const res = await fetch(`${API_BASE}/api/expenses/${expenseId}`, { method: "DELETE" });
    if (res.ok) {
      showToast("Deleted", "Expense entry removed.", "info");
      loadExpenses();
      loadOverview();
      loadBudgets();
    }
  } catch (err) {
    showToast("Error", "Could not delete expense.", "error");
  }
}

/**
 * Load Category Budgets with Live Spending Status
 */
async function loadBudgets() {
  if (!currentStudentId || currentStudentId <= 0) {
    console.warn("Cannot load budgets: Invalid student ID");
    return;
  }
  const container = document.getElementById("budgets-container");
  if (!container) return;

  try {
    const res = await fetch(`${API_BASE}/api/budgets/${currentStudentId}/status`);
    if (!res.ok) return;
    const budgets = await res.json();

    if (budgets.length === 0) {
      container.innerHTML = `<p style="color: var(--text-muted); font-size: 0.85rem;">No category budgets set. Click '+ Set Budget Limit' above.</p>`;
      return;
    }

    container.innerHTML = budgets
      .map((b) => {
        const spent = b.total_spent || 0.0;
        const limit = b.monthly_limit || 1.0;
        const remaining = b.remaining !== undefined ? b.remaining : Math.max(0, limit - spent);
        const pct = Math.min(100, Math.round(b.percentage_used || 0));
        const color = b.status === "Exceeded" || pct >= 100 
          ? "var(--accent-rose)" 
          : b.status === "Warning" || pct >= 80 
          ? "var(--accent-amber)" 
          : "var(--accent-emerald)";

        const statusLabel = b.status === "Exceeded" 
          ? `Exceeded (${pct}%)` 
          : b.status === "Warning" 
          ? `Near Limit (${pct}%)` 
          : `${pct}% Used`;

        const isExceeded = b.status === "Exceeded" || pct >= 100;
        const cardClass = isExceeded ? "glass-card budget-card-exceeded" : "glass-card";

        return `
          <div class="${cardClass}" style="position: relative;">
            <div class="card-header-row">
              <h4>${escapeHtml(b.category)}</h4>
              <div style="display: flex; align-items: center; gap: 0.5rem;">
                <span class="badge-pill" style="color: ${color};">${statusLabel}</span>
                <button onclick="handleDeleteBudget(${b.budget_id})" title="Delete Budget" style="background: transparent; border: none; color: var(--text-dim); cursor: pointer; font-size: 1.1rem; line-height: 1; padding: 0 4px;">&times;</button>
              </div>
            </div>
            <div style="font-size: 1.25rem; font-weight: 700; margin: 0.5rem 0;">
              ${currencySymbol}${spent.toFixed(2)} <span style="font-size: 0.85rem; color: var(--text-muted); font-weight: 400;">/ ${currencySymbol}${limit.toFixed(2)}</span>
            </div>
            <div style="width: 100%; height: 8px; background: rgba(255,255,255,0.08); border-radius: 4px; overflow: hidden; margin-top: 0.5rem;">
              <div style="width: ${pct}%; height: 100%; background: ${color}; border-radius: 4px;"></div>
            </div>
            <div style="font-size: 0.78rem; color: var(--text-muted); margin-top: 0.65rem; display: flex; justify-content: space-between;">
              <span>Remaining: ${currencySymbol}${remaining.toFixed(2)}</span>
              <span>${pct}% used</span>
            </div>
          </div>
        `;
      })
      .join("");
  } catch (err) {
    console.error("Error loading budgets:", err);
  }
}

/**
 * Handle Delete Budget Limit
 */
async function handleDeleteBudget(budgetId) {
  if (!confirm("Are you sure you want to delete this budget limit?")) return;
  try {
    const res = await fetch(`${API_BASE}/api/budgets/${budgetId}`, { method: "DELETE" });
    if (res.ok) {
      showToast("Budget Removed", "Category budget limit deleted.", "info");
      loadBudgets();
    }
  } catch (err) {
    showToast("Error", "Could not delete budget limit.", "error");
  }
}

/**
 * Load Savings Goals
 */
async function loadGoals() {
  if (!currentStudentId || currentStudentId <= 0) {
    console.warn("Cannot load goals: Invalid student ID");
    return;
  }
  const container = document.getElementById("goals-container");
  if (!container) return;

  try {
    const res = await fetch(`${API_BASE}/api/goals/${currentStudentId}`);
    if (!res.ok) return;
    const goals = await res.json();

    if (goals.length === 0) {
      container.innerHTML = `<p style="color: var(--text-muted); font-size: 0.85rem;">No savings goals created yet. Click '+ Create Savings Goal' above.</p>`;
      return;
    }

    container.innerHTML = goals
      .map((g) => {
        const current = g.current_amount || 0.0;
        const target = g.target_amount || 1.0;
        const pct = Math.min(100, Math.round((current / target) * 100));

        return `
          <div class="glass-card">
            <div class="card-header-row">
              <h4>${escapeHtml(g.title)}</h4>
              <span class="tag-badge">${g.status || 'In Progress'}</span>
            </div>
            <div style="font-size: 1.25rem; font-weight: 700; margin: 0.5rem 0;">
              ${currencySymbol}${current.toFixed(2)} <span style="font-size: 0.85rem; color: var(--text-muted); font-weight: 400;">of ${currencySymbol}${target.toFixed(2)}</span>
            </div>
            <div style="width: 100%; height: 8px; background: rgba(255,255,255,0.08); border-radius: 4px; overflow: hidden; margin-top: 0.5rem;">
              <div style="width: ${pct}%; height: 100%; background: var(--accent-cyan); border-radius: 4px;"></div>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 1rem;">
              <span style="font-size: 0.78rem; color: var(--text-dim);">Due: ${g.deadline}</span>
              <button class="btn btn-secondary btn-sm" onclick="openDepositModal(${g.id}, '${escapeHtml(g.title)}')">+ Deposit</button>
            </div>
          </div>
        `;
      })
      .join("");
  } catch (err) {
    console.error("Error loading goals:", err);
  }
}

/**
 * Load AI Recommendations
 */
async function loadRecommendations() {
  if (!currentStudentId || currentStudentId <= 0) {
    console.warn("Cannot load recommendations: Invalid student ID");
    return;
  }
  const container = document.getElementById("recs-cards-container");
  const countBadge = document.getElementById("recs-count-badge");
  if (!container) return;

  try {
    const res = await fetch(`${API_BASE}/api/recommendations/${currentStudentId}`);
    if (!res.ok) return;
    const recs = await res.json();

    if (countBadge) countBadge.textContent = `${recs.length} Suggestions`;

    if (recs.length === 0) {
      container.innerHTML = `<p style="color: var(--text-muted); font-size: 0.85rem;">No active recommendations. Click 'Generate Fresh AI Advice' above!</p>`;
      return;
    }

    container.innerHTML = recs
      .map((r) => {
        const impactColor = r.impact_level === "High" ? "var(--accent-rose)" : r.impact_level === "Medium" ? "var(--accent-amber)" : "var(--accent-emerald)";
        return `
          <div class="glass-card" style="border-left: 3px solid ${impactColor};">
            <div class="card-header-row">
              <h4>${escapeHtml(r.title)}</h4>
              <span class="badge-pill" style="color: ${impactColor};">${r.impact_level} Priority</span>
            </div>
            <p style="font-size: 0.88rem; color: var(--text-muted); margin: 0.75rem 0;">${escapeHtml(r.message)}</p>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 0.5rem;">
              <span class="tag-badge">${escapeHtml(r.category)}</span>
              <button class="btn btn-secondary btn-sm" onclick="handleDismissRec(${r.id})">Dismiss</button>
            </div>
          </div>
        `;
      })
      .join("");
  } catch (err) {
    console.error("Error loading recommendations:", err);
  }
}

/**
 * Trigger AI Recommendation Generation
 */
async function triggerGenerateRecommendations() {
  if (!currentStudentId) return;
  const btnText = document.getElementById("ai-generate-text");
  const btnIcon = document.getElementById("ai-generate-icon");
  if (btnText) btnText.textContent = "Analyzing Habits with Gemini...";
  if (btnIcon) btnIcon.textContent = "";

  try {
    const res = await fetch(`${API_BASE}/api/recommendations/${currentStudentId}/generate`, { method: "POST" });
    if (res.ok) {
      showToast("AI Recommendations Updated", "Fresh financial advice generated from your recent habits.", "success");
      loadRecommendations();
    } else {
      showToast("Generation Error", "Could not generate recommendations.", "error");
    }
  } catch (err) {
    showToast("Network Error", "Failed to connect to recommendation service.", "error");
  } finally {
    if (btnText) btnText.textContent = "Generate Fresh AI Advice";
    if (btnIcon) btnIcon.textContent = "";
  }
}

/**
 * Handle Dismiss Recommendation
 */
async function handleDismissRec(recId) {
  try {
    const res = await fetch(`${API_BASE}/api/recommendations/${recId}`, { method: "DELETE" });
    if (res.ok) {
      loadRecommendations();
    }
  } catch (err) {
    console.warn("Could not dismiss recommendation:", err);
  }
}

/**
 * =========================================================================
 * Automatic Notification Simulation (Demo & Testing)
 * =========================================================================
 */

function fillSimulationPreset(text, source) {
  const textInput = document.getElementById("sim-text");
  const sourceSelect = document.getElementById("sim-source");
  if (textInput) textInput.value = text;
  if (sourceSelect) sourceSelect.value = source;
}

async function handleSimulateNotification(e) {
  e.preventDefault();
  if (!currentStudentId || currentStudentId <= 0) {
    showToast("No Student Selected", "Please select a valid student profile first.", "error");
    return;
  }

  const text = document.getElementById("sim-text").value.trim();
  const source = document.getElementById("sim-source").value;
  const submitBtn = document.getElementById("btn-submit-simulate");

  if (!text) return;
  if (submitBtn) submitBtn.disabled = true;

  try {
    const res = await fetch(`${API_BASE}/api/transactions/simulate-notification`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        student_id: currentStudentId,
        notification_text: text,
        source_app: source,
      }),
    });

    const data = await res.json();

    if (data.success && !data.is_duplicate) {
      showToast(
        "Transaction Detected & Recorded!",
        `${currencySymbol}${data.expense.amount.toFixed(2)} at ${data.expense.merchant || data.expense.title} categorized as ${data.expense.category}`,
        "success"
      );
      closeModal("modal-simulate-notification");
      document.getElementById("form-simulate-notification")?.reset();
      loadOverview();
      loadExpenses();
      loadTrackingStatus();
      loadBudgets();
      if (data.budget_alert) {
        checkAndShowBudgetAlert(data.budget_alert);
      } else {
        loadBudgetAlerts();
      }
    } else if (data.is_duplicate) {
      showToast(
        "Duplicate Transaction Ignored",
        "This payment notification was already recorded. Deduplication prevented double-counting.",
        "info"
      );
      closeModal("modal-simulate-notification");
    } else if (data.ignored) {
      showToast(
        "Notification Filtered Out",
        `${data.ignore_reason || 'Non-financial or failed notification ignored safely.'}`,
        "info"
      );
      closeModal("modal-simulate-notification");
    } else {
      showToast("Detection Error", data.message || "Could not process notification.", "error");
    }
  } catch (err) {
    showToast("Connection Error", "Could not reach the backend.", "error");
  } finally {
    if (submitBtn) submitBtn.disabled = false;
  }
}

/**
 * Handle Manual Expense Creation
 */
async function handleCreateExpense(e) {
  e.preventDefault();
  if (!currentStudentId || currentStudentId <= 0) {
    showToast("No Student Selected", "Please select or register a student profile first.", "error");
    openStudentModal();
    return;
  }

  const titleEl = document.getElementById("exp-title");
  const amountEl = document.getElementById("exp-amount");
  const catEl = document.getElementById("exp-category");
  const dateEl = document.getElementById("exp-date");
  const paymentEl = document.getElementById("exp-payment");
  const notesEl = document.getElementById("exp-notes");

  const title = titleEl ? titleEl.value.trim() : "";
  const amount = amountEl ? parseFloat(amountEl.value) : 0;
  const category = catEl ? catEl.value : "Others";
  const dateVal = dateEl && dateEl.value ? dateEl.value : new Date().toISOString().split("T")[0];
  const payment = paymentEl ? paymentEl.value : "UPI";
  const notes = notesEl ? notesEl.value.trim() : "";

  if (!title) {
    showToast("Validation Error", "Please enter an expense title/description.", "error");
    return;
  }

  if (isNaN(amount) || amount <= 0) {
    showToast("Validation Error", "Please enter a valid expense amount greater than 0.", "error");
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/api/expenses/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        student_id: currentStudentId,
        title,
        amount,
        category,
        date: dateVal,
        payment_method: payment,
        notes,
      }),
    });

    if (res.ok) {
      const expData = await res.json();
      showToast("Expense Saved", `${currencySymbol}${amount.toFixed(2)} logged under ${category}.`, "success");
      closeModal("modal-add-expense");
      document.getElementById("form-add-expense")?.reset();
      loadOverview();
      loadExpenses();
      loadBudgets();
      if (expData.budget_alert) {
        checkAndShowBudgetAlert(expData.budget_alert);
      } else {
        loadBudgetAlerts();
      }
    } else {
      const errData = await res.json().catch(() => ({}));
      const detail = typeof errData.detail === "string" ? errData.detail : "Could not save expense. Please check input values.";
      showToast("Error Saving Expense", detail, "error");
    }
  } catch (err) {
    showToast("Network Error", "Could not connect to server.", "error");
  }
}

/**
 * Handle Create Budget
 */
async function handleCreateBudget(e) {
  e.preventDefault();
  if (!currentStudentId || currentStudentId <= 0) {
    showToast("No Student Selected", "Please select a valid student profile first.", "error");
    return;
  }

  const category = document.getElementById("bgt-category").value;
  const monthly_limit = parseFloat(document.getElementById("bgt-limit").value);
  const now = new Date();

  try {
    const res = await fetch(`${API_BASE}/api/budgets/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        student_id: currentStudentId,
        category,
        monthly_limit,
        month: now.getMonth() + 1,
        year: now.getFullYear(),
      }),
    });

    if (res.ok) {
      showToast("Budget Set", `Limit of ${currencySymbol}${monthly_limit.toFixed(2)} established for ${category}.`, "success");
      closeModal("modal-add-budget");
      document.getElementById("form-add-budget")?.reset();
      loadBudgets();
      loadOverview();
    }
  } catch (err) {
    showToast("Error", "Could not set budget.", "error");
  }
}

/**
 * Handle Create Goal
 */
async function handleCreateGoal(e) {
  e.preventDefault();
  if (!currentStudentId || currentStudentId <= 0) {
    showToast("No Student Selected", "Please select a valid student profile first.", "error");
    return;
  }

  const title = document.getElementById("goal-title").value.trim();
  const target_amount = parseFloat(document.getElementById("goal-target").value);
  const current_amount = parseFloat(document.getElementById("goal-initial").value || 0);
  const deadline = document.getElementById("goal-deadline").value;

  try {
    const res = await fetch(`${API_BASE}/api/goals/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        student_id: currentStudentId,
        title,
        target_amount,
        current_amount,
        deadline,
      }),
    });

    if (res.ok) {
      showToast("Goal Created", `Target of ${currencySymbol}${target_amount.toFixed(2)} set for '${title}'.`, "success");
      closeModal("modal-add-goal");
      document.getElementById("form-add-goal")?.reset();
      loadGoals();
    }
  } catch (err) {
    showToast("Error", "Could not create goal.", "error");
  }
}

/**
 * Open Deposit Modal
 */
function openDepositModal(goalId, title) {
  document.getElementById("deposit-goal-id").value = goalId;
  document.getElementById("deposit-goal-name").textContent = `Contributing funds towards '${title}'`;
  openModal("modal-deposit-goal");
}

/**
 * Handle Deposit Goal
 */
async function handleDepositGoal(e) {
  e.preventDefault();
  const goalId = document.getElementById("deposit-goal-id").value;
  const amount = parseFloat(document.getElementById("deposit-amount").value);

  try {
    const res = await fetch(`${API_BASE}/api/goals/${goalId}/deposit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ amount }),
    });

    if (res.ok) {
      showToast("Deposit Confirmed", `Deposited ${currencySymbol}${amount.toFixed(2)} towards goal!`, "success");
      closeModal("modal-deposit-goal");
      document.getElementById("form-deposit-goal")?.reset();
      loadGoals();
    }
  } catch (err) {
    showToast("Error", "Could not complete deposit.", "error");
  }
}

/**
 * Student Profile & Switching
 */
function updateSidebarProfile() {
  if (!currentStudent) return;
  const avatar = document.getElementById("sidebar-user-avatar");
  const name = document.getElementById("sidebar-user-name");
  const year = document.getElementById("sidebar-user-year");

  if (name) name.textContent = currentStudent.name || "Student";
  if (year) year.textContent = `${currentStudent.college_year || 'Undergrad'} • ${currencySymbol}${(currentStudent.monthly_allowance || 0).toFixed(0)}/mo`;
  if (avatar) {
    const initials = (currentStudent.name || "S").split(" ").map((n) => n[0]).join("").toUpperCase().slice(0, 2);
    avatar.textContent = initials;
  }
}

function openStudentModal() {
  openModal("modal-student");
}

function onStudentSelectChanged(newId) {
  const parsedId = parseInt(newId);
  if (!parsedId || parsedId <= 0) {
    showToast("Invalid Selection", "Please select a valid student.", "error");
    return;
  }
  
  currentStudentId = parsedId;
  localStorage.setItem("activeStudentId", currentStudentId);
  closeModal("modal-student");
  initApp();
}

function populateStudentSelect(students) {
  const sel = document.getElementById("select-active-student");
  if (!sel) return;
  const activeStudentId = currentStudentId || (currentStudent ? currentStudent.id : 0);
  const activeStudent = (students && activeStudentId ? students.find((s) => s.id === activeStudentId) : null) || currentStudent || (students && students.length > 0 ? students[0] : null);
  if (!activeStudent) {
    sel.innerHTML = "";
    return;
  }
  sel.innerHTML = `<option value="${activeStudent.id}" selected>${escapeHtml(activeStudent.name)} (${activeStudent.email})</option>`;
}

async function handleRegisterStudent(e) {
  e.preventDefault();
  const name = document.getElementById("stud-name").value.trim();
  const email = document.getElementById("stud-email").value.trim();
  const password = document.getElementById("stud-password").value;
  const monthly_allowance = parseFloat(document.getElementById("stud-allowance").value);
  const college_year = document.getElementById("stud-year").value;

  try {
    const res = await apiFetch("/api/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name,
        email,
        password,
        monthly_allowance,
        currency: "INR",
        college_year: college_year,
      }),
    });

    if (res.ok) {
      const data = await res.json();
      authToken = data.access_token;
      localStorage.setItem("authToken", authToken);
      showToast("Welcome Aboard!", `Profile created for ${name}.`, "success");
      closeModal("modal-student");
      initApp();
    } else {
      const err = await res.json();
      showToast("Registration Error", err.detail || "Could not register student.", "error");
    }
  } catch (err) {
    showToast("Error", "Could not connect to server.", "error");
  }
}

async function handleLoginStudent(e) {
  e.preventDefault();
  const email = document.getElementById("login-email").value;
  const password = document.getElementById("login-password").value;

  try {
    const params = new URLSearchParams();
    params.append('username', email);
    params.append('password', password);

    const res = await fetch(`${API_BASE}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: params.toString(),
    });

    if (res.ok) {
      const data = await res.json();
      authToken = data.access_token;
      localStorage.setItem("authToken", authToken);
      showToast("Login Successful", "Welcome back!", "success");
      closeModal("modal-student");
      initApp();
    } else {
      const err = await res.json();
      showToast("Login Failed", err.detail || "Invalid credentials", "error");
    }
  } catch (err) {
    showToast("Error", "Could not connect to server.", "error");
  }
}

function logoutStudent() {
  authToken = null;
  currentStudentId = 0;
  currentStudent = null;
  localStorage.removeItem("authToken");
  localStorage.removeItem("activeStudentId");
  document.querySelectorAll(".tab-view").forEach((tab) => tab.classList.remove("active"));
  openStudentModal();
}

async function createDefaultStudent() {
  try {
    const res = await fetch(`${API_BASE}/api/onboarding/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: "Aryan Sharma",
        email: "aryan@campus.edu",
        monthly_allowance: 12000.0,
        currency: "INR",
        college_year: "Sophomore",
      }),
    });
    if (res.ok) {
      currentStudent = await res.json();
      currentStudentId = currentStudent.id;
      localStorage.setItem("activeStudentId", currentStudentId);
      showToast("Welcome!", "Default student profile created.", "success");
      // Reload the app with the new student
      await initApp();
    } else {
      showToast("Error", "Could not create default student profile.", "error");
    }
  } catch (e) {
    showToast("Connection Error", "Could not connect to backend to create student.", "error");
  }
}

/**
 * Modal Utilities
 */
function openModal(modalId) {
  const m = document.getElementById(modalId);
  if (m) m.classList.add("active");
}

function closeModal(modalId) {
  const m = document.getElementById(modalId);
  if (m) m.classList.remove("active");
}

/**
 * Toast Notifications
 */
function showToast(title, message, type = "info") {
  const container = document.getElementById("toast-container");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = `toast-item ${type}`;
  toast.style.cssText = `
    background: rgba(17, 24, 39, 0.95);
    backdrop-filter: blur(12px);
    border: 1px solid ${type === "success" ? "rgba(16, 185, 129, 0.4)" : type === "error" ? "rgba(244, 63, 94, 0.4)" : "rgba(99, 102, 241, 0.4)"};
    border-left: 4px solid ${type === "success" ? "var(--accent-emerald)" : type === "error" ? "var(--accent-rose)" : "var(--primary)"};
    border-radius: var(--radius-sm);
    padding: 0.85rem 1rem;
    margin-top: 0.5rem;
    box-shadow: 0 10px 25px rgba(0,0,0,0.5);
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
    min-width: 280px;
    max-width: 420px;
    animation: toast-in 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  `;

  toast.innerHTML = `
    <div style="font-weight: 600; font-size: 0.88rem; color: #fff;">${escapeHtml(title)}</div>
    <div style="font-size: 0.80rem; color: rgba(255, 255, 255, 0.85);">${escapeHtml(message)}</div>
  `;

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(20px)";
    toast.style.transition = "all 0.3s ease";
    setTimeout(() => toast.remove(), 300);
  }, 4500);
}

function formatTimeAgo(date) {
  const seconds = Math.floor((new Date() - date) / 1000);
  if (seconds < 10) return "Just now";
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
