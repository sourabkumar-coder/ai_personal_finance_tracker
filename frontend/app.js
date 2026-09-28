/**
 * AI Personal Finance Tracker - Frontend Application Engine
 * Connects to FastAPI backend, manages state, renders glassmorphic components,
 * and handles live 4-second polling for automatic UPI transaction detection.
 */

// Configuration
const API_BASE =
  typeof window !== "undefined" && (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1")
    ? "http://localhost:8000"
    : "https://ai-personal-finance-tracker-9wo5.onrender.com";

if (typeof window !== "undefined") {
  window.API_BASE = API_BASE;
}

// Global State
let currentStudentId = parseInt(localStorage.getItem("activeStudentId")) || 0;
let currentStudent = null;
let currentCurrency = "INR";
let currencySymbol = "₹";
let previousExpenseCount = 0;
let pollingInterval = null;
let authToken = localStorage.getItem("authToken") || null;
// Guards the session-expired UX so one expiry produces one prompt, not one per request.
let sessionExpiredNotified = false;

function stopPolling() {
  if (pollingInterval) {
    clearInterval(pollingInterval);
    pollingInterval = null;
  }
}

function resetSessionExpiredFlag() {
  sessionExpiredNotified = false;
}

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
    stopPolling();
    if (!sessionExpiredNotified) {
      sessionExpiredNotified = true;
      showLoginScreen();
      showToast("Session Expired", "Please login again.", "error");
    }
  }
  return res;
}

if (typeof window !== "undefined") {
  window.apiFetch = apiFetch;
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
  if (!authToken && (!currentStudentId || currentStudentId <= 0)) {
    showLoginScreen();
    return;
  }
  try {
    let loaded = false;
    if (authToken) {
      const meRes = await apiFetch("/api/auth/me");
      if (meRes.ok) {
        currentStudent = await meRes.json();
        currentStudentId = currentStudent.id;
        localStorage.setItem("activeStudentId", currentStudentId);
        loaded = true;
      }
    }
    if (!loaded && currentStudentId > 0) {
      const profRes = await apiFetch(`/api/onboarding/profile/${currentStudentId}`);
      if (profRes.ok) {
        currentStudent = await profRes.json();
        loaded = true;
      }
    }
    if (loaded && currentStudent) {
      currentCurrency = currentStudent.currency || "INR";
      currencySymbol = currentCurrency === "INR" ? "₹" : "$";
      updateSidebarProfile();
      loadAllViews();
      hideLoginScreen();
      resetSessionExpiredFlag();
      setupPolling();
    } else {
      showLoginScreen();
    }
  } catch (err) {
    console.error("Init error", err);
    showLoginScreen();
  }
}

/**
 * Toggle Login Screen
 */
function showLoginScreen() {
  const loginScreen = document.getElementById("login-screen");
  const appDashboard = document.getElementById("app-dashboard");
  if (loginScreen) loginScreen.style.display = "flex";
  if (appDashboard) appDashboard.style.display = "none";
}

function hideLoginScreen() {
  const loginScreen = document.getElementById("login-screen");
  const appDashboard = document.getElementById("app-dashboard");
  if (loginScreen) loginScreen.style.display = "none";
  if (appDashboard) appDashboard.style.display = "flex";
}

/**
 * Switch between Login and Register tabs on the Auth screen
 */
function switchAuthTab(tab) {
  const loginTab = document.getElementById("auth-tab-login");
  const registerTab = document.getElementById("auth-tab-register");
  const loginPanel = document.getElementById("auth-panel-login");
  const registerPanel = document.getElementById("auth-panel-register");
  const authAlert = document.getElementById("auth-alert");

  if (authAlert) authAlert.style.display = "none";

  if (tab === "login") {
    if (loginTab) loginTab.classList.add("active");
    if (registerTab) registerTab.classList.remove("active");
    if (loginPanel) loginPanel.style.display = "block";
    if (registerPanel) registerPanel.style.display = "none";
  } else {
    if (registerTab) registerTab.classList.add("active");
    if (loginTab) loginTab.classList.remove("active");
    if (registerPanel) registerPanel.style.display = "block";
    if (loginPanel) loginPanel.style.display = "none";
  }
}

/**
 * Handle Login Form Submit
 */
async function handleLoginStudent(event) {
  if (event) event.preventDefault();
  const emailInput = document.getElementById("login-email");
  const passwordInput = document.getElementById("login-password");
  const submitBtn = document.getElementById("btn-submit-login");

  const email = emailInput ? emailInput.value.trim() : "";
  const password = passwordInput ? passwordInput.value : "";

  if (!email || !password) {
    showAuthAlert("Please enter both email and password.", "error");
    return;
  }

  const defaultBtnContent = `<span>Sign In to Account</span><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>`;
  setButtonLoading(submitBtn, true, "Logging in...");

  try {
    const formData = new URLSearchParams();
    formData.append("username", email);
    formData.append("password", password);

    let res = await apiFetch(`${API_BASE}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: formData,
    });

    if (res.ok) {
      const data = await res.json();
      authToken = data.access_token;
      localStorage.setItem("authToken", authToken);
      resetSessionExpiredFlag();
      if (data.student && data.student.id) {
        currentStudentId = data.student.id;
        localStorage.setItem("activeStudentId", currentStudentId);
      }

      showAuthAlert("Login successful! Redirecting...", "success");
      showToast("Welcome Back!", "Logged in successfully.", "success");

      setupPolling();
      setTimeout(async () => {
        await initApp();
      }, 400);
    } else {
      const errData = await res.json().catch(() => ({}));
      const msg = errData.detail || "Incorrect email or password. Please try again.";
      showAuthAlert(msg, "error");
      showToast("Login Failed", msg, "error");
    }
  } catch (err) {
    console.error("Login error:", err);
    showAuthAlert("Cannot connect to server. Please check network connection.", "error");
    showToast("Connection Error", "Cannot reach backend server", "error");
  } finally {
    setButtonLoading(submitBtn, false, defaultBtnContent);
  }
}

/**
 * Handle Registration Form Submit
 */
async function handleRegisterStudent(event) {
  if (event) event.preventDefault();
  const nameInput = document.getElementById("stud-name");
  const emailInput = document.getElementById("stud-email");
  const passwordInput = document.getElementById("stud-password");
  const allowanceInput = document.getElementById("stud-allowance");
  const yearInput = document.getElementById("stud-year");
  const submitBtn = document.getElementById("btn-submit-register");

  const name = nameInput ? nameInput.value.trim() : "";
  const email = emailInput ? emailInput.value.trim() : "";
  const password = passwordInput ? passwordInput.value : "";
  const allowance = allowanceInput ? parseFloat(allowanceInput.value) : 0;
  const year = yearInput ? yearInput.value : "First Year";

  if (!name || !email || !password || !allowance) {
    showAuthAlert("Please fill in all required fields.", "error");
    return;
  }

  const defaultBtnContent = `<span>Create Student Account</span><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>`;
  setButtonLoading(submitBtn, true, "Creating Account...");

  try {
    const payload = {
      name,
      email,
      password,
      monthly_allowance: allowance,
      college_year: year,
      currency: "INR"
    };

    let res = await apiFetch(`${API_BASE}/api/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (res.status === 404) {
      res = await apiFetch(`${API_BASE}/api/onboarding/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    }

    if (res.ok) {
      const data = await res.json();
      if (data.access_token) {
        authToken = data.access_token;
        localStorage.setItem("authToken", authToken);
      }
      resetSessionExpiredFlag();
      if (data.student && data.student.id) {
        currentStudentId = data.student.id;
        localStorage.setItem("activeStudentId", currentStudentId);
      } else if (data.id) {
        currentStudentId = data.id;
        localStorage.setItem("activeStudentId", currentStudentId);
      }

      showAuthAlert("Account created successfully!", "success");
      showToast("Registration Complete", "Welcome to SmartFinance AI!", "success");

      setupPolling();
      setTimeout(async () => {
        await initApp();
      }, 400);
    } else {
      const errData = await res.json().catch(() => ({}));
      const msg = errData.detail || "Registration failed. Email may already be registered.";
      showAuthAlert(msg, "error");
      showToast("Registration Failed", msg, "error");
    }
  } catch (err) {
    console.error("Registration error:", err);
    showAuthAlert("Cannot connect to server. Please check network connection.", "error");
    showToast("Connection Error", "Cannot reach backend server", "error");
  } finally {
    setButtonLoading(submitBtn, false, defaultBtnContent);
  }
}

/**
 * Handle Student Logout
 */
function logoutStudent() {
  authToken = null;
  currentStudent = null;
  currentStudentId = 0;
  localStorage.removeItem("authToken");
  localStorage.removeItem("activeStudentId");
  stopPolling();
  resetSessionExpiredFlag();
  showLoginScreen();
  showToast("Logged Out", "You have been safely logged out.", "info");
}

/**
 * Update Sidebar User Profile Card
 */
function updateSidebarProfile() {
  if (!currentStudent) return;
  const nameEl = document.getElementById("sidebar-user-name");
  const yearEl = document.getElementById("sidebar-user-year");
  const avatarEl = document.getElementById("sidebar-user-avatar");

  if (nameEl) nameEl.textContent = currentStudent.name || "Student User";
  if (yearEl) {
    const year = currentStudent.college_year || "Student";
    const allowance = currentStudent.monthly_allowance
      ? `${currencySymbol}${currentStudent.monthly_allowance.toLocaleString()}/mo`
      : "";
    yearEl.textContent = `${year} • ${allowance}`;
  }
  if (avatarEl) {
    const initials = (currentStudent.name || "SU")
      .trim()
      .split(" ")
      .map((n) => n[0])
      .join("")
      .substring(0, 2)
      .toUpperCase();
    avatarEl.textContent = initials || "SF";
  }
}

function showAuthAlert(message, type = "error") {
  const alertEl = document.getElementById("auth-alert");
  if (!alertEl) return;
  alertEl.textContent = message;
  alertEl.className = `auth-alert ${type}`;
  alertEl.style.display = "flex";
}

function setButtonLoading(btn, isLoading, defaultHtml) {
  if (!btn) return;
  btn.disabled = isLoading;
  if (isLoading) {
    btn.innerHTML = `<span class="auth-spinner"></span> ${defaultHtml}`;
  } else {
    btn.innerHTML = defaultHtml;
  }
}

// Expose on window for inline HTML event attributes
window.switchAuthTab = switchAuthTab;
window.handleLoginStudent = handleLoginStudent;
window.handleRegisterStudent = handleRegisterStudent;
window.logoutStudent = logoutStudent;
window.updateSidebarProfile = updateSidebarProfile;


/**
 * Setup 4-second live polling for auto-detected transactions.
 */
function setupPolling() {
  if (pollingInterval) clearInterval(pollingInterval);
  pollingInterval = setInterval(async () => {
    if (!authToken) return;
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
    const res = await apiFetch(`${API_BASE}/api/expenses/${currentStudentId}`);
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
        if (typeof loadTrends === "function") loadTrends();
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
  loadSplitBalances();
  if (typeof loadTrends === "function") loadTrends();
}

/**
 * Load & Render Active Budget Exceeded / Warning Banners
 */
async function loadBudgetAlerts() {
  if (!currentStudentId || currentStudentId <= 0) return;
  const banner = document.getElementById("budget-alert-banner");
  if (!banner) return;

  try {
    const res = await apiFetch(`${API_BASE}/api/budgets/${currentStudentId}/alerts`);
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
    trends: "Expense Trends",
    "ai-advisor": "AI Financial Advisor",
    expenses: "Itemized Expenses",
    budgets: "Monthly Budgets",
    goals: "Financial Savings Goals",
    "auto-tracking": "Automatic UPI & Bank Detection",
    "split-bills": "Split Bills & Shared Expenses",
  };
  const topHeading = document.getElementById("top-page-heading");
  if (topHeading) topHeading.textContent = headingMap[tabId] || "Financial Overview";

  // Reload tab-specific data
  if (tabId === "overview") loadOverview();
  if (tabId === "trends" && typeof loadTrends === "function") loadTrends();
  if (tabId === "expenses") loadExpenses();
  if (tabId === "budgets") loadBudgets();
  if (tabId === "goals") loadGoals();
  if (tabId === "ai-advisor") loadRecommendations();
  if (tabId === "auto-tracking") {
    loadTrackingStatus();
    loadTrackingSettings();
  }
  if (tabId === "split-bills") {
    loadSplitBillsView();
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
    const profRes = await apiFetch(`${API_BASE}/api/onboarding/profile/${currentStudentId}`);
    if (profRes.ok) {
      currentStudent = await profRes.json();
      currentCurrency = currentStudent.currency || "INR";
      currencySymbol = currentCurrency === "INR" ? "₹" : "$";
      updateSidebarProfile();
    }

    // 2. Analytics Overview
    const analyticsRes = await apiFetch(`${API_BASE}/api/analytics/${currentStudentId}/overview`);
    if (analyticsRes.ok) {
      const a = await analyticsRes.json();
      const allowance = a.monthly_allowance || 0.0;
      const spent = a.total_spent || 0.0;
      const remaining = a.remaining_balance || 0.0;
      const pct = allowance > 0 ? ((spent / allowance) * 100).toFixed(1) : 0;

      const elAllowance = document.getElementById("val-monthly-allowance");
      if (elAllowance) elAllowance.textContent = `${currencySymbol}${allowance.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

      const elCurrency = document.getElementById("val-monthly-currency");
      if (elCurrency) elCurrency.textContent = `${currentCurrency} / Month`;

      const elSpent = document.getElementById("val-total-spent");
      if (elSpent) elSpent.textContent = `${currencySymbol}${spent.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

      const elSpentPct = document.getElementById("val-spent-pct");
      if (elSpentPct) elSpentPct.textContent = `${pct}% of monthly allowance`;

      const elRemaining = document.getElementById("val-remaining-balance");
      if (elRemaining) elRemaining.textContent = `${currencySymbol}${remaining.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

      const daysInMonth = 30;
      const day = new Date().getDate();
      const daysLeft = Math.max(1, daysInMonth - day);
      const safeDaily = remaining > 0 ? (remaining / daysLeft).toFixed(2) : "0.00";
      const elDaily = document.getElementById("val-daily-budget");
      if (elDaily) elDaily.textContent = `Safe daily spend: ${currencySymbol}${safeDaily}`;
    }

    // 2b. Category Breakdown
    const catRes = await apiFetch(`${API_BASE}/api/analytics/${currentStudentId}/by-category`);
    if (catRes.ok) {
      const catData = await catRes.json();
      renderCategoryList(catData);
    }

    // 3. Forecast
    const fcRes = await apiFetch(`${API_BASE}/api/recommendations/${currentStudentId}/forecast`);
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
    const expRes = await apiFetch(`${API_BASE}/api/expenses/${currentStudentId}`);
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
    const res = await apiFetch(`${API_BASE}/api/onboarding/profile/${currentStudentId}`, {
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
    const res = await apiFetch(`${API_BASE}/api/transactions/${currentStudentId}/status`);
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
    const res = await apiFetch(`${API_BASE}/api/transactions/${currentStudentId}/settings`);
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
    const res = await apiFetch(`${API_BASE}/api/transactions/${currentStudentId}/settings`, {
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
    const res = await apiFetch(`${API_BASE}/api/expenses/${expenseId}`, { method: "DELETE" });
    if (res.ok) {
      showToast("Deleted", "Expense entry removed.", "info");
      loadExpenses();
      loadOverview();
      loadBudgets();
      if (typeof loadTrends === "function") loadTrends();
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
    const res = await apiFetch(`${API_BASE}/api/budgets/${currentStudentId}/status`);
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
    const res = await apiFetch(`${API_BASE}/api/budgets/${budgetId}`, { method: "DELETE" });
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
    const res = await apiFetch(`${API_BASE}/api/goals/${currentStudentId}`);
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
    const res = await apiFetch(`${API_BASE}/api/recommendations/${currentStudentId}`);
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
  if (btnText) btnText.textContent = "Analyzing Habits with Groq AI...";
  if (btnIcon) btnIcon.textContent = "";

  try {
    const res = await apiFetch(`${API_BASE}/api/recommendations/${currentStudentId}/generate`, { method: "POST" });
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
    const res = await apiFetch(`${API_BASE}/api/recommendations/${recId}`, { method: "DELETE" });
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
    const res = await apiFetch(`${API_BASE}/api/transactions/simulate-notification`, {
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
      if (typeof loadTrends === "function") loadTrends();
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
    openModal("modal-student");
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
  const typeEl = document.getElementById("exp-type");
  const transaction_type = typeEl ? typeEl.value : "EXPENSE";

  if (!title) {
    showToast("Validation Error", "Please enter an expense title/description.", "error");
    return;
  }

  if (isNaN(amount) || amount <= 0) {
    showToast("Validation Error", "Please enter a valid expense amount greater than 0.", "error");
    return;
  }

  try {
    const res = await apiFetch(`${API_BASE}/api/expenses/`, {
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
        transaction_type,
      }),
    });

    if (res.ok) {
      const expData = await res.json();
      const label = transaction_type === "INCOME" ? "Income Deposit" : "Expense";
      showToast(`${label} Saved`, `${currencySymbol}${amount.toFixed(2)} logged under ${category}.`, "success");

      if (expData.auto_savings_synced) {
        showToast("🎉 20% Auto-Savings Synced!", expData.auto_savings_synced.message, "success");
      }

      closeModal("modal-add-expense");
      document.getElementById("form-add-expense")?.reset();
      loadOverview();
      loadExpenses();
      loadBudgets();
      loadGoals();
      if (typeof loadTrends === "function") loadTrends();
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
    const res = await apiFetch(`${API_BASE}/api/budgets/`, {
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
    const res = await apiFetch(`${API_BASE}/api/goals/`, {
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
    const res = await apiFetch(`${API_BASE}/api/goals/${goalId}/deposit`, {
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
function openStudentModal() {
  showLoginScreen();
}

function onStudentSelectChanged(newId) {
  const parsedId = parseInt(newId);
  if (!parsedId || parsedId <= 0) {
    showToast("Invalid Selection", "Please select a valid student.", "error");
    return;
  }

  currentStudentId = parsedId;
  localStorage.setItem("activeStudentId", currentStudentId);
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

async function createDefaultStudent() {
  try {
    const res = await apiFetch("/api/onboarding/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: "Aryan Sharma",
        email: "aryan@campus.edu",
        monthly_allowance: 12000.0,
        currency: "INR",
        college_year: "First Year",
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

// ==========================================================================
// Split Bills Feature Module
// ==========================================================================

let currentSplitGroupId = null;
let currentSplitGroups = [];
let splitBillParticipants = [];
let currentWhatsAppReminderText = "";

/**
 * Main coordinator to load all Split Bills sub-views
 */
async function loadSplitBillsView() {
  if (!currentStudentId || currentStudentId <= 0) return;
  await Promise.all([
    loadSplitBalances(),
    loadSplitGroups(),
    loadSplitBillsList(),
    loadSplitSettlements(),
  ]);
}

/**
 * Fetch and render consolidated balances and per-friend ledger
 */
async function loadSplitBalances() {
  if (!currentStudentId || currentStudentId <= 0) return;
  const container = document.getElementById("friend-balances-container");
  const owedToYouEl = document.getElementById("val-split-owed-to-you");
  const youOweEl = document.getElementById("val-split-you-owe");
  const netBalanceEl = document.getElementById("val-split-net-balance");
  const netSubtextEl = document.getElementById("val-split-net-subtext");
  const activeCountBadge = document.getElementById("badge-active-splits-count");

  try {
    const url = `${API_BASE}/api/split-bills/balances/${currentStudentId}${
      currentSplitGroupId ? `?group_id=${currentSplitGroupId}` : ""
    }`;
    const res = await apiFetch(url);
    if (!res.ok) {
      console.warn("Could not load split balances:", res.status);
      return;
    }
    const data = await res.json();

    const owedToYou = data.total_owed_to_you || 0;
    const youOwe = data.total_you_owe || 0;
    const net = data.net_balance || 0;
    const activeCount = data.active_splits_count || 0;

    if (owedToYouEl) owedToYouEl.textContent = `${currencySymbol}${owedToYou.toFixed(2)}`;
    if (youOweEl) youOweEl.textContent = `${currencySymbol}${youOwe.toFixed(2)}`;
    if (activeCountBadge) activeCountBadge.textContent = `${activeCount} Active`;

    if (netBalanceEl) {
      if (net > 0.01) {
        netBalanceEl.className = "metric-value text-emerald";
        netBalanceEl.textContent = `+${currencySymbol}${net.toFixed(2)}`;
      } else if (net < -0.01) {
        netBalanceEl.className = "metric-value text-amber";
        netBalanceEl.textContent = `-${currencySymbol}${Math.abs(net).toFixed(2)}`;
      } else {
        netBalanceEl.className = "metric-value";
        netBalanceEl.textContent = `${currencySymbol}0.00`;
      }
    }

    if (netSubtextEl) {
      if (net > 0.01) {
        netSubtextEl.textContent = `You are owed ${currencySymbol}${net.toFixed(2)} in total`;
      } else if (net < -0.01) {
        netSubtextEl.textContent = `You owe ${currencySymbol}${Math.abs(net).toFixed(2)} in total`;
      } else {
        netSubtextEl.textContent = "All debts settled";
      }
    }

    // Render Friends Balances List
    if (!container) return;
    const friends = data.friends || [];

    if (friends.length === 0) {
      container.innerHTML = `
        <div class="empty-state-card" style="text-align: center; padding: 2.5rem 1rem; color: var(--text-muted);">
          <div style="font-size: 2.2rem; margin-bottom: 0.5rem;">🤝</div>
          <h4 style="margin: 0 0 0.35rem 0; color: var(--text-main); font-size: 1rem;">No Shared Debts Yet</h4>
          <p style="font-size: 0.85rem; max-width: 320px; margin: 0 auto 1.25rem auto;">Create a split group or log a shared dinner, flat bill, or ride to track who owes who.</p>
          <button class="btn btn-primary btn-sm" onclick="openModalSplitBill()">+ Split a Bill</button>
        </div>
      `;
      return;
    }

    let html = "";
    friends.forEach((f) => {
      const isOwedToYou = f.status === "OWED_TO_YOU";
      const isYouOwe = f.status === "YOU_OWE";
      const isSettled = f.status === "SETTLED";

      const initials = (f.name || "F")
        .split(" ")
        .map((p) => p[0])
        .slice(0, 2)
        .join("")
        .toUpperCase();

      const absAmount = Math.abs(f.net_balance || 0);

      let statusBadge = "";
      let amountClass = "";
      let actionButtons = "";

      if (isOwedToYou) {
        statusBadge = `<span class="badge-pill" style="background: rgba(15, 68, 34, 0.1); color: var(--accent-emerald); font-weight: 600;">Owes You</span>`;
        amountClass = "text-emerald";
        const waMsg =
          f.whatsapp_message ||
          `Hey ${f.name}, you have a pending split of ${currencySymbol}${absAmount.toFixed(
            2
          )} on SmartFinance. Please settle when you get a chance!`;
        actionButtons = `
          <button class="btn btn-secondary btn-xs" onclick="openWhatsAppModal('${escapeHtml(
            f.name
          )}', ${absAmount}, '${encodeURIComponent(waMsg)}')">
            <span>💬 Remind</span>
          </button>
          <button class="btn btn-primary btn-xs" onclick="openModalRecordSettlement('${escapeHtml(
            f.name
          )}', ${absAmount}, 'THEY_PAID_YOU', ${f.group_id || "null"}, null)">
            <span>✓ Settle Up</span>
          </button>
        `;
      } else if (isYouOwe) {
        statusBadge = `<span class="badge-pill" style="background: rgba(217, 119, 6, 0.12); color: var(--accent-amber); font-weight: 600;">You Owe</span>`;
        amountClass = "text-amber";
        const upiAction = f.upi_link
          ? `<a href="${f.upi_link}" class="btn btn-magic btn-xs" style="text-decoration:none;" target="_blank"><span>⚡ Pay UPI</span></a>`
          : "";
        actionButtons = `
          ${upiAction}
          <button class="btn btn-primary btn-xs" onclick="openModalRecordSettlement('${escapeHtml(
            f.name
          )}', ${absAmount}, 'YOU_PAID_THEM', ${f.group_id || "null"}, '${f.upi_id || ""}')">
            <span>✓ Settle Up</span>
          </button>
        `;
      } else {
        statusBadge = `<span class="badge-pill" style="background: #E2E8F0; color: var(--text-muted);">Settled</span>`;
        amountClass = "text-muted";
        actionButtons = `
          <button class="btn btn-ghost btn-xs" onclick="openModalSplitBill('${escapeHtml(f.name)}')">
            <span>+ New Bill</span>
          </button>
        `;
      }

      html += `
        <div class="friend-balance-card glass-card">
          <div class="friend-card-header">
            <div class="friend-avatar-wrap">
              <div class="friend-avatar">${initials}</div>
              <div>
                <div class="friend-name-text">${escapeHtml(f.name)}</div>
                ${f.group_name ? `<div class="friend-group-tag">👥 ${escapeHtml(f.group_name)}</div>` : ""}
              </div>
            </div>
            <div style="text-align: right;">
              <div class="friend-balance-amount ${amountClass}">
                ${isSettled ? `${currencySymbol}0.00` : `${currencySymbol}${absAmount.toFixed(2)}`}
              </div>
              <div style="margin-top: 0.15rem;">${statusBadge}</div>
            </div>
          </div>
          <div class="friend-card-actions">
            ${actionButtons}
          </div>
        </div>
      `;
    });

    container.innerHTML = html;
  } catch (err) {
    console.error("Error loading split balances:", err);
  }
}

/**
 * Load student's split groups and render filter chips
 */
async function loadSplitGroups() {
  if (!currentStudentId || currentStudentId <= 0) return;
  const chipsContainer = document.getElementById("split-groups-chips");
  const groupSelect = document.getElementById("split-group-select");

  try {
    const res = await apiFetch(`${API_BASE}/api/split-bills/groups/${currentStudentId}`);
    if (!res.ok) return;
    currentSplitGroups = await res.json();

    // Render filter chips
    if (chipsContainer) {
      let chipsHtml = `
        <button class="filter-chip ${currentSplitGroupId === null ? "active" : ""}" id="chip-group-all" onclick="filterSplitGroup(null)">
          All Splits
        </button>
      `;
      currentSplitGroups.forEach((g) => {
        const isActive = currentSplitGroupId === g.id;
        chipsHtml += `
          <button class="filter-chip ${isActive ? "active" : ""}" id="chip-group-${g.id}" onclick="filterSplitGroup(${g.id})">
            ${escapeHtml(g.name)} (${g.bills_count || 0})
          </button>
        `;
      });
      chipsContainer.innerHTML = chipsHtml;
    }

    // Populate split bill modal group select
    if (groupSelect) {
      let optionsHtml = `<option value="">Direct / Standalone Friends</option>`;
      currentSplitGroups.forEach((g) => {
        const isSelected = currentSplitGroupId === g.id ? "selected" : "";
        optionsHtml += `<option value="${g.id}" ${isSelected}>${escapeHtml(g.name)} (${(g.members || []).length} members)</option>`;
      });
      groupSelect.innerHTML = optionsHtml;
    }
  } catch (err) {
    console.error("Error loading split groups:", err);
  }
}

/**
 * Filter Split Bills by Split Group (or null for all)
 */
function filterSplitGroup(groupId) {
  currentSplitGroupId = groupId;
  document.querySelectorAll(".split-groups-filter .filter-chip").forEach((chip) => chip.classList.remove("active"));
  const targetChip =
    groupId === null
      ? document.getElementById("chip-group-all")
      : document.getElementById(`chip-group-${groupId}`);
  if (targetChip) targetChip.classList.add("active");

  loadSplitBalances();
  loadSplitBillsList();
  loadSplitSettlements();
}

/**
 * Load Shared Bills Table
 */
async function loadSplitBillsList() {
  if (!currentStudentId || currentStudentId <= 0) return;
  const tbody = document.getElementById("tbody-split-bills");
  if (!tbody) return;

  try {
    const url = `${API_BASE}/api/split-bills/bills/${currentStudentId}${
      currentSplitGroupId ? `?group_id=${currentSplitGroupId}` : ""
    }`;
    const res = await apiFetch(url);
    if (!res.ok) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 2rem;">Error loading shared bills.</td></tr>`;
      return;
    }
    const bills = await res.json();

    if (bills.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="6" style="text-align: center; color: var(--text-muted); padding: 2.5rem 1rem;">
            No shared bills found. Click <strong>+ Split a Bill</strong> to log your first shared expense!
          </td>
        </tr>
      `;
      return;
    }

    let html = "";
    bills.forEach((b) => {
      const isYouPayer =
        (b.payer_name || "").toLowerCase() === "you" ||
        (currentStudent && (b.payer_name || "").toLowerCase() === currentStudent.name.toLowerCase());
      const impactText = isYouPayer
        ? `<div style="font-size: 0.76rem; color: var(--accent-emerald); font-weight: 600;">+${currencySymbol}${(
            b.your_net_impact || 0
          ).toFixed(2)} to collect</div>`
        : `<div style="font-size: 0.76rem; color: var(--accent-amber); font-weight: 600;">-${currencySymbol}${(
            b.your_share || 0
          ).toFixed(2)} you owe</div>`;

      html += `
        <tr>
          <td>
            <div style="font-weight: 600; color: var(--text-main);">${escapeHtml(b.title)}</div>
            <div style="font-size: 0.78rem; color: var(--text-muted); margin-top: 0.15rem;">
              <span>${b.date}</span> · <span class="tag-badge">${escapeHtml(b.category)}</span>
              ${
                b.split_type === "EXACT"
                  ? '<span class="badge-pill" style="font-size:0.68rem; margin-left:0.25rem;">Exact</span>'
                  : ""
              }
            </div>
          </td>
          <td>
            ${
              b.group_name
                ? `<span class="badge-pill">${escapeHtml(b.group_name)}</span>`
                : '<span style="color:var(--text-muted); font-size:0.82rem;">Direct</span>'
            }
          </td>
          <td style="font-weight: 700; color: var(--text-main);">
            ${currencySymbol}${b.total_amount.toFixed(2)}
          </td>
          <td>
            <span style="font-weight: 500;">${escapeHtml(b.payer_name)}</span>
          </td>
          <td>
            <div style="font-weight: 600;">${currencySymbol}${(b.your_share || 0).toFixed(2)}</div>
            ${impactText}
          </td>
          <td>
            <button class="btn btn-ghost btn-xs text-rose" onclick="handleDeleteSplitBill(${b.id})" title="Delete Split Bill">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
            </button>
          </td>
        </tr>
      `;
    });
    tbody.innerHTML = html;
  } catch (err) {
    console.error("Error loading split bills:", err);
  }
}

/**
 * Load Settlements History Table
 */
async function loadSplitSettlements() {
  if (!currentStudentId || currentStudentId <= 0) return;
  const tbody = document.getElementById("tbody-split-settlements");
  if (!tbody) return;

  try {
    const url = `${API_BASE}/api/split-bills/settlements/${currentStudentId}${
      currentSplitGroupId ? `?group_id=${currentSplitGroupId}` : ""
    }`;
    const res = await apiFetch(url);
    if (!res.ok) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 2rem;">Error loading settlements.</td></tr>`;
      return;
    }
    const settlements = await res.json();

    if (settlements.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="6" style="text-align: center; color: var(--text-muted); padding: 2.5rem 1rem;">
            No settlements recorded yet. Settle up with a friend to see completed payments here!
          </td>
        </tr>
      `;
      return;
    }

    let html = "";
    settlements.forEach((s) => {
      html += `
        <tr>
          <td style="font-size: 0.85rem; color: var(--text-muted);">${s.settlement_date}</td>
          <td style="font-weight: 600;">${escapeHtml(s.from_name)}</td>
          <td style="font-weight: 600;">${escapeHtml(s.to_name)}</td>
          <td style="font-weight: 700; color: var(--accent-emerald);">
            ${currencySymbol}${s.amount.toFixed(2)}
          </td>
          <td>
            <span class="badge-pill">${escapeHtml(s.payment_method)}</span>
          </td>
          <td>
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <span style="font-size: 0.82rem; color: var(--text-muted);">${escapeHtml(s.notes || "—")}</span>
              <button class="btn btn-ghost btn-xs text-rose" onclick="handleDeleteSettlement(${s.id})" title="Delete Settlement Record">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
              </button>
            </div>
          </td>
        </tr>
      `;
    });
    tbody.innerHTML = html;
  } catch (err) {
    console.error("Error loading split settlements:", err);
  }
}

/**
 * Switch Sub-tabs between Shared Bills and Settlements
 */
function switchSplitSubtab(subtab) {
  const btnBills = document.getElementById("btn-subtab-bills");
  const btnSettlements = document.getElementById("btn-subtab-settlements");
  const subviewBills = document.getElementById("split-subview-bills");
  const subviewSettlements = document.getElementById("split-subview-settlements");

  if (subtab === "bills") {
    if (btnBills) btnBills.classList.add("active");
    if (btnSettlements) btnSettlements.classList.remove("active");
    if (subviewBills) {
      subviewBills.classList.add("active");
      subviewBills.style.display = "block";
    }
    if (subviewSettlements) {
      subviewSettlements.classList.remove("active");
      subviewSettlements.style.display = "none";
    }
    loadSplitBillsList();
  } else {
    if (btnSettlements) btnSettlements.classList.add("active");
    if (btnBills) btnBills.classList.remove("active");
    if (subviewSettlements) {
      subviewSettlements.classList.add("active");
      subviewSettlements.style.display = "block";
    }
    if (subviewBills) {
      subviewBills.classList.remove("active");
      subviewBills.style.display = "none";
    }
    loadSplitSettlements();
  }
}

/**
 * Open Modal to Split a Bill
 */
function openModalSplitBill(initialFriendName = null) {
  const form = document.getElementById("form-split-bill");
  if (form) form.reset();

  const dateEl = document.getElementById("split-date");
  if (dateEl) dateEl.value = new Date().toISOString().split("T")[0];

  const groupSelect = document.getElementById("split-group-select");
  if (groupSelect) {
    groupSelect.value = currentSplitGroupId !== null ? String(currentSplitGroupId) : "";
  }

  setSplitType("EQUAL");

  // Initial participants
  splitBillParticipants = [{ name: "You", id: null, amount: 0, isYou: true }];

  // If a group is currently active, populate its members
  if (groupSelect && groupSelect.value) {
    onSplitGroupSelected();
  } else if (initialFriendName && initialFriendName !== "You") {
    splitBillParticipants.push({ name: initialFriendName, id: null, amount: 0, isYou: false });
    renderSplitParticipantsList();
    updatePayerSelect();
  } else {
    renderSplitParticipantsList();
    updatePayerSelect();
  }

  recalculateSplitShares();

  const friendInput = document.getElementById("input-quick-friend-name");
  if (friendInput) {
    friendInput.onkeydown = (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        addQuickParticipant();
      }
    };
  }

  openModal("modal-split-bill");
}

/**
 * Handle group selection inside Split Bill modal
 */
function onSplitGroupSelected() {
  const groupSelect = document.getElementById("split-group-select");
  const selectedGroupId = groupSelect && groupSelect.value ? parseInt(groupSelect.value) : null;

  splitBillParticipants = [{ name: "You", id: null, amount: 0, isYou: true }];

  if (selectedGroupId && currentSplitGroups) {
    const grp = currentSplitGroups.find((g) => g.id === selectedGroupId);
    if (grp && grp.members) {
      grp.members.forEach((m) => {
        const mName = m.name.trim();
        if (
          mName.toLowerCase() !== "you" &&
          (!currentStudent || mName.toLowerCase() !== currentStudent.name.toLowerCase())
        ) {
          splitBillParticipants.push({
            name: mName,
            id: m.id,
            amount: 0,
            isYou: false,
          });
        }
      });
    }
  }

  renderSplitParticipantsList();
  updatePayerSelect();
  recalculateSplitShares();
}

/**
 * Update the 'Who Paid?' select dropdown
 */
function updatePayerSelect() {
  const payerSelect = document.getElementById("split-payer-select");
  if (!payerSelect) return;
  const currentVal = payerSelect.value;

  let optionsHtml = `<option value="You">You (paid entire bill)</option>`;
  splitBillParticipants.forEach((p) => {
    if (!p.isYou) {
      optionsHtml += `<option value="${escapeHtml(p.name)}">${escapeHtml(p.name)}</option>`;
    }
  });

  payerSelect.innerHTML = optionsHtml;
  if (
    currentVal &&
    splitBillParticipants.some((p) => p.name === currentVal || (p.isYou && currentVal === "You"))
  ) {
    payerSelect.value = currentVal;
  }
}

/**
 * Switch Split Method (EQUAL vs EXACT)
 */
function setSplitType(type) {
  const typeInput = document.getElementById("split-type");
  const btnEqual = document.getElementById("btn-split-equal");
  const btnExact = document.getElementById("btn-split-exact");

  if (typeInput) typeInput.value = type;
  if (type === "EXACT") {
    if (btnExact) btnExact.classList.add("active");
    if (btnEqual) btnEqual.classList.remove("active");
  } else {
    if (btnEqual) btnEqual.classList.add("active");
    if (btnExact) btnExact.classList.remove("active");
  }

  renderSplitParticipantsList();
  recalculateSplitShares();
}

/**
 * Render dynamic participants inside Split Bill modal
 */
function renderSplitParticipantsList() {
  const container = document.getElementById("split-participants-list");
  if (!container) return;

  const splitType = (document.getElementById("split-type") || {}).value || "EQUAL";
  const isExact = splitType === "EXACT";

  let html = "";
  splitBillParticipants.forEach((p, idx) => {
    const initials = p.name
      .split(" ")
      .map((s) => s[0])
      .slice(0, 2)
      .join("")
      .toUpperCase();

    html += `
      <div class="participant-item-row">
        <div class="participant-info">
          <div class="friend-avatar" style="width: 28px; height: 28px; font-size: 0.75rem;">${initials}</div>
          <span>${escapeHtml(p.name)}</span>
          ${p.isYou ? '<span class="participant-badge-you">You</span>' : ""}
        </div>
        <div class="participant-share-display">
          ${
            isExact
              ? `<span style="font-size:0.85rem; color:var(--text-muted);">${currencySymbol}</span>
                 <input type="number" step="0.50" min="0" class="form-control participant-exact-input" 
                        value="${p.amount || ""}" placeholder="0.00" 
                        oninput="onParticipantExactAmountChange(${idx}, this.value)">`
              : `<span id="share-display-${idx}" style="font-weight: 600; color: var(--text-main); font-size: 0.88rem;">${currencySymbol}0.00</span>`
          }
          ${
            !p.isYou
              ? `<button type="button" class="btn-remove-participant" onclick="removeParticipant(${idx})" title="Remove participant">&times;</button>`
              : '<span style="width: 1.25rem;"></span>'
          }
        </div>
      </div>
    `;
  });

  container.innerHTML = html;
}

/**
 * Handler for exact amount change on participant row
 */
function onParticipantExactAmountChange(index, val) {
  if (splitBillParticipants[index]) {
    splitBillParticipants[index].amount = parseFloat(val) || 0;
  }
  recalculateSplitShares();
}

/**
 * Add a quick friend participant by name
 */
function addQuickParticipant() {
  const input = document.getElementById("input-quick-friend-name");
  if (!input) return;
  const name = input.value.trim();
  if (!name) return;

  const exists = splitBillParticipants.some((p) => p.name.toLowerCase() === name.toLowerCase());
  if (exists) {
    showToast("Already Added", `${name} is already in the split list.`, "info");
    input.value = "";
    return;
  }

  splitBillParticipants.push({
    name: name,
    id: null,
    amount: 0,
    isYou: false,
  });

  input.value = "";
  renderSplitParticipantsList();
  updatePayerSelect();
  recalculateSplitShares();
}

/**
 * Remove participant from the active split bill
 */
function removeParticipant(index) {
  if (splitBillParticipants[index] && splitBillParticipants[index].isYou) {
    showToast("Notice", "You cannot remove yourself from the bill.", "info");
    return;
  }
  splitBillParticipants.splice(index, 1);
  renderSplitParticipantsList();
  updatePayerSelect();
  recalculateSplitShares();
}

/**
 * Recalculate shares summary (Equal or Exact)
 */
function recalculateSplitShares() {
  const totalInput = document.getElementById("split-total-amount");
  const summaryEl = document.getElementById("split-shares-summary");
  const splitType = (document.getElementById("split-type") || {}).value || "EQUAL";

  const total = parseFloat(totalInput ? totalInput.value : 0) || 0;
  const n = splitBillParticipants.length;

  if (!summaryEl) return;

  if (splitType === "EQUAL") {
    if (n === 0 || total <= 0) {
      summaryEl.textContent = `${currencySymbol}0.00 / person`;
      return;
    }
    const share = (total / n).toFixed(2);
    summaryEl.textContent = `${currencySymbol}${share} / person (${n} splitters)`;

    // Update each participant's share display
    splitBillParticipants.forEach((p, idx) => {
      p.amount = parseFloat(share);
      const displayEl = document.getElementById(`share-display-${idx}`);
      if (displayEl) displayEl.textContent = `${currencySymbol}${share}`;
    });
  } else {
    // Exact split breakdown
    const currentSum = splitBillParticipants.reduce((acc, p) => acc + (parseFloat(p.amount) || 0), 0);
    const diff = total - currentSum;

    if (total <= 0) {
      summaryEl.innerHTML = `<span style="color:var(--text-muted);">Enter total bill amount</span>`;
    } else if (Math.abs(diff) < 0.05) {
      summaryEl.innerHTML = `<span style="color: var(--accent-emerald); font-weight:700;">✓ Exact match (${currencySymbol}${total.toFixed(
        2
      )})</span>`;
    } else if (diff > 0) {
      summaryEl.innerHTML = `<span style="color: var(--accent-amber);">Remaining: ${currencySymbol}${diff.toFixed(
        2
      )}</span>`;
    } else {
      summaryEl.innerHTML = `<span style="color: var(--accent-rose);">Exceeds by ${currencySymbol}${Math.abs(
        diff
      ).toFixed(2)}</span>`;
    }
  }
}

/**
 * Handle form submission to create a Split Bill
 */
async function handleCreateSplitBill(event) {
  if (event) event.preventDefault();

  if (!currentStudentId || currentStudentId <= 0) {
    showToast("Auth Required", "Please log in first.", "error");
    return;
  }

  const title = (document.getElementById("split-title") || {}).value.trim();
  const totalAmount = parseFloat((document.getElementById("split-total-amount") || {}).value) || 0;
  const groupIdVal = (document.getElementById("split-group-select") || {}).value;
  const category = (document.getElementById("split-category") || {}).value || "Food";
  const dateVal =
    (document.getElementById("split-date") || {}).value || new Date().toISOString().split("T")[0];
  const payerName = (document.getElementById("split-payer-select") || {}).value || "You";
  const splitType = (document.getElementById("split-type") || {}).value || "EQUAL";
  const syncExpense = !!(document.getElementById("split-sync-expense") || {}).checked;
  const notes = (document.getElementById("split-notes") || {}).value.trim();
  const submitBtn = document.getElementById("btn-submit-split-bill");

  if (!title) {
    showToast("Title Required", "Please enter a bill description.", "error");
    return;
  }

  if (totalAmount <= 0) {
    showToast("Invalid Amount", "Please enter a valid total amount.", "error");
    return;
  }

  if (splitBillParticipants.length < 2) {
    showToast("Add Friends", "Please add at least one friend to split this bill with.", "error");
    return;
  }

  // If EXACT, validate shares sum
  if (splitType === "EXACT") {
    const sum = splitBillParticipants.reduce((acc, p) => acc + (parseFloat(p.amount) || 0), 0);
    if (Math.abs(sum - totalAmount) > 0.05) {
      showToast(
        "Mismatch",
        `The exact shares total (${currencySymbol}${sum.toFixed(
          2
        )}) must equal the total bill (${currencySymbol}${totalAmount.toFixed(2)}).`,
        "error"
      );
      return;
    }
  }

  const payload = {
    student_id: currentStudentId,
    group_id: groupIdVal ? parseInt(groupIdVal) : null,
    title: title,
    total_amount: totalAmount,
    category: category,
    date: dateVal,
    payer_name: payerName,
    split_type: splitType,
    notes: notes || null,
    sync_to_expenses: syncExpense,
    shares: splitBillParticipants.map((p) => ({
      member_name: p.name,
      member_id: p.id || null,
      share_amount: splitType === "EXACT" ? parseFloat(p.amount) || 0 : null,
    })),
  };

  setButtonLoading(submitBtn, true, "Saving Split...");

  try {
    const res = await apiFetch(`${API_BASE}/api/split-bills/bills`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (res.ok) {
      closeModal("modal-split-bill");
      showToast(
        "Split Bill Saved!",
        `Bill '${title}' split among ${splitBillParticipants.length} people.`,
        "success"
      );
      loadSplitBillsView();
      if (syncExpense) {
        loadExpenses();
        loadOverview();
        loadBudgetAlerts();
      }
    } else {
      const err = await res.json().catch(() => ({}));
      showToast("Error", err.detail || "Failed to create split bill.", "error");
    }
  } catch (e) {
    console.error("Error creating split bill:", e);
    showToast("Network Error", "Could not connect to server.", "error");
  } finally {
    setButtonLoading(submitBtn, false, "Save Split Bill");
  }
}

/**
 * Delete a Split Bill
 */
async function handleDeleteSplitBill(billId) {
  if (
    !confirm("Are you sure you want to delete this split bill? Any synced personal expense will also be removed.")
  ) {
    return;
  }

  try {
    const res = await apiFetch(`${API_BASE}/api/split-bills/bills/${billId}?student_id=${currentStudentId}`, {
      method: "DELETE",
    });

    if (res.ok || res.status === 204) {
      showToast("Split Bill Deleted", "The bill has been deleted.", "success");
      loadSplitBillsView();
      loadExpenses();
      loadOverview();
    } else {
      showToast("Error", "Could not delete split bill.", "error");
    }
  } catch (e) {
    console.error("Error deleting split bill:", e);
    showToast("Network Error", "Could not connect to server.", "error");
  }
}

/**
 * Handle Create Split Group
 */
async function handleCreateGroup(event) {
  if (event) event.preventDefault();

  if (!currentStudentId || currentStudentId <= 0) {
    showToast("Auth Required", "Please log in first.", "error");
    return;
  }

  const nameInput = document.getElementById("group-name");
  const descInput = document.getElementById("group-desc");
  const submitBtn = document.getElementById("btn-submit-create-group");

  const name = nameInput ? nameInput.value.trim() : "";
  const desc = descInput ? descInput.value.trim() : "";

  if (!name) {
    showToast("Group Name Required", "Please enter a name for the group.", "error");
    return;
  }

  // Gather initial members
  const memberRows = document.querySelectorAll("#new-group-members-container .member-input-row");
  const initialMembers = [];
  memberRows.forEach((row) => {
    const nameEl = row.querySelector(".new-member-name");
    const upiEl = row.querySelector(".new-member-upi");
    const mName = nameEl ? nameEl.value.trim() : "";
    const mUpi = upiEl ? upiEl.value.trim() : "";
    if (mName) {
      initialMembers.push({
        name: mName,
        upi_id: mUpi || null,
      });
    }
  });

  const payload = {
    student_id: currentStudentId,
    name: name,
    description: desc || null,
    initial_members: initialMembers,
  };

  setButtonLoading(submitBtn, true, "Creating Group...");

  try {
    const res = await apiFetch(`${API_BASE}/api/split-bills/groups`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (res.ok) {
      closeModal("modal-create-group");
      const form = document.getElementById("form-create-group");
      if (form) form.reset();
      showToast("Group Created", `Group '${name}' created successfully.`, "success");
      loadSplitBillsView();
    } else {
      const err = await res.json().catch(() => ({}));
      showToast("Error", err.detail || "Failed to create group.", "error");
    }
  } catch (e) {
    console.error("Error creating group:", e);
    showToast("Network Error", "Could not connect to server.", "error");
  } finally {
    setButtonLoading(submitBtn, false, "Create Group");
  }
}

/**
 * Add another member input row in Create Group modal
 */
function addNewGroupMemberInput() {
  const container = document.getElementById("new-group-members-container");
  if (!container) return;

  const div = document.createElement("div");
  div.className = "member-input-row";
  div.style.display = "flex";
  div.style.gap = "0.5rem";
  div.style.marginBottom = "0.5rem";
  div.innerHTML = `
    <input type="text" class="form-control new-member-name" placeholder="Friend's Full Name">
    <input type="text" class="form-control new-member-upi" placeholder="UPI ID (optional)">
    <button type="button" class="btn btn-ghost btn-xs text-rose" onclick="this.parentElement.remove()" title="Remove row">&times;</button>
  `;
  container.appendChild(div);
}

/**
 * Open Modal to Record Settlement
 */
function openModalRecordSettlement(friendName, amount, direction, groupId, upiId) {
  const friendNameInput = document.getElementById("settle-friend-name");
  const groupIdInput = document.getElementById("settle-group-id");
  const displayNameEl = document.getElementById("settle-display-name");
  const displayAmountEl = document.getElementById("settle-display-amount");
  const amountInput = document.getElementById("settle-amount");
  const directionSelect = document.getElementById("settle-direction-select");
  const directionText = document.getElementById("settle-direction-text");
  const upiBox = document.getElementById("settle-upi-box");
  const upiLink = document.getElementById("settle-upi-link");

  const absAmount = Math.abs(amount || 0);

  if (friendNameInput) friendNameInput.value = friendName;
  if (groupIdInput) groupIdInput.value = groupId || "";
  if (displayNameEl) displayNameEl.textContent = friendName;
  if (displayAmountEl) displayAmountEl.textContent = `${currencySymbol}${absAmount.toFixed(2)}`;
  if (amountInput) amountInput.value = absAmount.toFixed(2);
  if (directionSelect) directionSelect.value = direction;

  if (directionText) {
    directionText.textContent =
      direction === "THEY_PAID_YOU"
        ? `Settling debt: ${friendName} owes you`
        : `Settling debt: You owe ${friendName}`;
  }

  // Handle UPI link for paying friend
  if (direction === "YOU_PAID_THEM" && upiId) {
    if (upiBox) upiBox.style.display = "block";
    if (upiLink) {
      upiLink.href = `upi://pay?pa=${upiId}&pn=${encodeURIComponent(friendName)}&am=${absAmount.toFixed(
        2
      )}&cu=INR`;
    }
  } else {
    if (upiBox) upiBox.style.display = "none";
  }

  // Attach listener for direction change if not already attached
  if (directionSelect) {
    directionSelect.onchange = () => {
      const dir = directionSelect.value;
      if (directionText) {
        directionText.textContent =
          dir === "THEY_PAID_YOU"
            ? `Settling debt: ${friendName} paid you`
            : `Settling debt: You paid ${friendName}`;
      }
      if (dir === "THEY_PAID_YOU" && upiBox) {
        upiBox.style.display = "none";
      } else if (dir === "YOU_PAID_THEM" && upiId && upiBox) {
        upiBox.style.display = "block";
      }
    };
  }

  openModal("modal-settle-up");
}

/**
 * Handle Settlement Form Submission
 */
async function handleSettleUp(event) {
  if (event) event.preventDefault();

  if (!currentStudentId || currentStudentId <= 0) {
    showToast("Auth Required", "Please log in first.", "error");
    return;
  }

  const friendName = (document.getElementById("settle-friend-name") || {}).value;
  const groupIdVal = (document.getElementById("settle-group-id") || {}).value;
  const amountVal = parseFloat((document.getElementById("settle-amount") || {}).value) || 0;
  const direction = (document.getElementById("settle-direction-select") || {}).value;
  const method = (document.getElementById("settle-method") || {}).value || "UPI";
  const notes = (document.getElementById("settle-notes") || {}).value.trim();

  if (!friendName || amountVal <= 0) {
    showToast("Invalid Amount", "Please enter a valid settlement amount.", "error");
    return;
  }

  const fromName = direction === "THEY_PAID_YOU" ? friendName : "You";
  const toName = direction === "THEY_PAID_YOU" ? "You" : friendName;

  const payload = {
    student_id: currentStudentId,
    group_id: groupIdVal ? parseInt(groupIdVal) : null,
    from_name: fromName,
    to_name: toName,
    amount: amountVal,
    payment_method: method,
    notes: notes || null,
  };

  try {
    const res = await apiFetch(`${API_BASE}/api/split-bills/settle`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (res.ok) {
      closeModal("modal-settle-up");
      showToast(
        "Settlement Recorded",
        `Recorded payment of ${currencySymbol}${amountVal.toFixed(2)} between You and ${friendName}.`,
        "success"
      );
      loadSplitBillsView();
    } else {
      const err = await res.json().catch(() => ({}));
      showToast("Error", err.detail || "Failed to record settlement.", "error");
    }
  } catch (e) {
    console.error("Error recording settlement:", e);
    showToast("Network Error", "Could not connect to server.", "error");
  }
}

/**
 * Delete a recorded settlement
 */
async function handleDeleteSettlement(settlementId) {
  if (!confirm("Are you sure you want to delete this settlement record?")) return;

  try {
    const res = await apiFetch(
      `${API_BASE}/api/split-bills/settlements/${settlementId}?student_id=${currentStudentId}`,
      {
        method: "DELETE",
      }
    );

    if (res.ok || res.status === 204) {
      showToast("Settlement Deleted", "The settlement record has been removed.", "success");
      loadSplitBillsView();
    } else {
      showToast("Error", "Could not delete settlement.", "error");
    }
  } catch (e) {
    console.error("Error deleting settlement:", e);
    showToast("Network Error", "Could not connect to server.", "error");
  }
}

/**
 * Open WhatsApp Reminder Modal
 */
function openWhatsAppModal(friendName, amount, encodedMsg) {
  const textEl = document.getElementById("wa-reminder-text");
  const msg = encodedMsg
    ? decodeURIComponent(encodedMsg)
    : `Hey ${friendName}, you have a pending split of ${currencySymbol}${amount.toFixed(
        2
      )} for shared expenses on SmartFinance. Please settle when you get a chance!`;

  currentWhatsAppReminderText = msg;
  if (textEl) textEl.value = msg;

  openModal("modal-whatsapp-reminder");
}

/**
 * Copy pre-formatted WhatsApp message to clipboard
 */
function copyWhatsAppMessage() {
  const textEl = document.getElementById("wa-reminder-text");
  const text = textEl ? textEl.value : currentWhatsAppReminderText;

  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard
      .writeText(text)
      .then(() => {
        showToast("Copied!", "Message copied to clipboard.", "success");
      })
      .catch(() => {
        fallbackCopy(text);
      });
  } else {
    fallbackCopy(text);
  }
}

function fallbackCopy(text) {
  const textArea = document.createElement("textarea");
  textArea.value = text;
  document.body.appendChild(textArea);
  textArea.select();
  document.execCommand("copy");
  document.body.removeChild(textArea);
  showToast("Copied!", "Message copied to clipboard.", "success");
}

/**
 * Open WhatsApp chat / Web with pre-filled message
 */
function openWhatsAppChat() {
  const textEl = document.getElementById("wa-reminder-text");
  const text = textEl ? textEl.value : currentWhatsAppReminderText;
  const url = `https://api.whatsapp.com/send?text=${encodeURIComponent(text)}`;
  window.open(url, "_blank");
}

// Global Window Exports for Inline HTML Event Attributes
window.switchTab = switchTab;
window.switchAuthTab = switchAuthTab;
window.logoutStudent = logoutStudent;
window.openEditAllowanceModal = openEditAllowanceModal;
window.handleUpdateAllowance = handleUpdateAllowance;
window.loadExpenses = loadExpenses;
window.handleCreateExpense = handleCreateExpense;
window.handleDeleteExpense = handleDeleteExpense;
window.loadBudgets = loadBudgets;
window.handleCreateBudget = handleCreateBudget;
window.handleDeleteBudget = handleDeleteBudget;
window.loadGoals = loadGoals;
window.handleCreateGoal = handleCreateGoal;
window.openDepositModal = openDepositModal;
window.handleDepositGoal = handleDepositGoal;
window.loadRecommendations = loadRecommendations;
window.triggerGenerateRecommendations = triggerGenerateRecommendations;
window.handleDismissRec = handleDismissRec;
window.fillSimulationPreset = fillSimulationPreset;
window.handleSimulateNotification = handleSimulateNotification;
window.handleToggleSetting = handleToggleSetting;
window.openModal = openModal;
window.closeModal = closeModal;
window.handleLoginStudent = handleLoginStudent;
window.handleRegisterStudent = handleRegisterStudent;

// Split Bills Window Exports
window.loadSplitBillsView = loadSplitBillsView;
window.loadSplitBalances = loadSplitBalances;
window.loadSplitGroups = loadSplitGroups;
window.loadSplitBillsList = loadSplitBillsList;
window.loadSplitSettlements = loadSplitSettlements;
window.filterSplitGroup = filterSplitGroup;
window.switchSplitSubtab = switchSplitSubtab;
window.openModalSplitBill = openModalSplitBill;
window.onSplitGroupSelected = onSplitGroupSelected;
window.updatePayerSelect = updatePayerSelect;
window.setSplitType = setSplitType;
window.renderSplitParticipantsList = renderSplitParticipantsList;
window.onParticipantExactAmountChange = onParticipantExactAmountChange;
window.addQuickParticipant = addQuickParticipant;
window.removeParticipant = removeParticipant;
window.recalculateSplitShares = recalculateSplitShares;
window.handleCreateSplitBill = handleCreateSplitBill;
window.handleDeleteSplitBill = handleDeleteSplitBill;
window.handleCreateGroup = handleCreateGroup;
window.addNewGroupMemberInput = addNewGroupMemberInput;
window.openModalRecordSettlement = openModalRecordSettlement;
window.handleSettleUp = handleSettleUp;
window.handleDeleteSettlement = handleDeleteSettlement;
window.openWhatsAppModal = openWhatsAppModal;
window.copyWhatsAppMessage = copyWhatsAppMessage;
window.openWhatsAppChat = openWhatsAppChat;

