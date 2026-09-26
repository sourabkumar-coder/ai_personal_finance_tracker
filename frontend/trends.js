/**
 * Expense Trends - line graph of time (x) vs spend (y) + histogram of
 * spend per category.
 * Fetches bucketed data from GET /api/analytics/{student_id}/trends?granularity=
 * and per-category totals from GET /api/analytics/{student_id}/by-category,
 * rendering both with Chart.js. Loaded after app.js so it can reuse
 * currentStudentId, currencySymbol and showToast().
 */

/* global Chart, currentStudentId, currencySymbol, showToast */

let trendsChart = null;
let categoryChart = null;
let currentGranularity = "daily";

const TRENDS_SUBTITLES = {
  daily: "Daily spend for the last 30 days.",
  weekly: "Weekly spend for the last 12 weeks (weeks start Monday).",
  monthly: "Monthly spend for the last 12 months.",
};

// Bar colors cycle per category; first entries match the app theme.
const CATEGORY_PALETTE = [
  "#0F4422", "#0284C7", "#D97706", "#7C3AED",
  "#DC2626", "#059669", "#DB2777", "#4F46E5",
  "#EA580C", "#0891B2", "#65A30D", "#BE123C",
];

function getCurrencySymbol() {
  if (typeof currencySymbol !== "undefined" && currencySymbol) return currencySymbol;
  return "₹";
}

function getActiveStudentId() {
  if (typeof currentStudentId !== "undefined" && currentStudentId > 0) return currentStudentId;
  const stored = parseInt(localStorage.getItem("activeStudentId"), 10);
  return stored > 0 ? stored : 0;
}

function getApiBase() {
  if (typeof API_BASE !== "undefined" && API_BASE) return API_BASE;
  return "";
}

/**
 * Range toggle handler wired from index.html pill buttons.
 */
function switchTrendRange(granularity) {
  if (!["daily", "weekly", "monthly"].includes(granularity)) return;
  currentGranularity = granularity;
  document.querySelectorAll(".trend-toggle-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.granularity === granularity);
  });
  loadTrends(granularity);
}

/**
 * Fetch trend buckets and render. Safe to call on tab switch / polling.
 */
async function loadTrends(granularity) {
  const range = granularity || currentGranularity || "daily";
  currentGranularity = range;

  const studentId = getActiveStudentId();
  if (!studentId) return;

  const subtitle = document.getElementById("trends-subtitle");
  if (subtitle && TRENDS_SUBTITLES[range]) subtitle.textContent = TRENDS_SUBTITLES[range];

  const errEl = document.getElementById("trends-error");
  if (errEl) {
    errEl.style.display = "none";
    errEl.textContent = "";
  }

  // Chart.js is loaded via CDN; degrade gracefully when offline/blocked.
  if (typeof Chart === "undefined") {
    if (errEl) {
      errEl.textContent = "Chart library (Chart.js CDN) failed to load. Check your connection and reload.";
      errEl.style.display = "block";
    }
    return;
  }

  try {
    const res = await fetch(`${getApiBase()}/api/analytics/${studentId}/trends?granularity=${range}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const buckets = await res.json();
    renderTrendsChart(buckets || [], range);
  } catch (err) {
    console.error("Error loading trends:", err);
    if (errEl) {
      errEl.textContent = "Could not load trend data. Please try again.";
      errEl.style.display = "block";
    } else if (typeof showToast === "function") {
      showToast("Trends Error", "Could not load trend data.", "error");
    }
  }

  // Keep the per-category histogram in sync wherever the line graph refreshes
  // (tab switch, new/deleted expense, auto-detected UPI transaction).
  loadCategoryChart();
}

function renderTrendsChart(buckets, range) {
  const canvas = document.getElementById("trends-chart");
  const emptyEl = document.getElementById("trends-empty");
  if (!canvas) return;

  const labels = buckets.map((b) => b.label || b.date);
  const values = buckets.map((b) => Number(b.amount) || 0);
  const symbol = getCurrencySymbol();

  updateTrendsStats(buckets, values, symbol);

  const hasData = values.some((v) => v > 0);
  if (emptyEl) emptyEl.style.display = hasData ? "none" : "block";

  if (trendsChart) {
    trendsChart.destroy();
    trendsChart = null;
  }

  trendsChart = new Chart(canvas.getContext("2d"), {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: `Spend (${range})`,
          data: values,
          borderColor: "#0F4422",
          backgroundColor: "rgba(15, 68, 34, 0.10)",
          pointBackgroundColor: "#0F4422",
          pointRadius: range === "daily" ? 2 : 4,
          pointHoverRadius: 6,
          borderWidth: 2.5,
          tension: 0.3,
          fill: true,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => ` ${symbol}${Number(ctx.parsed.y).toFixed(2)}`,
          },
        },
      },
      scales: {
        x: {
          ticks: {
            maxRotation: 45,
            minRotation: 0,
            autoSkip: true,
            maxTicksLimit: range === "daily" ? 10 : 12,
          },
          grid: { display: false },
        },
        y: {
          beginAtZero: true,
          ticks: {
            callback: (v) => `${symbol}${v}`,
          },
        },
      },
    },
  });
}

function updateTrendsStats(buckets, values, symbol) {
  const totalEl = document.getElementById("trends-total");
  const avgEl = document.getElementById("trends-avg");
  const peakEl = document.getElementById("trends-peak");
  if (!totalEl || !avgEl || !peakEl) return;

  if (!buckets.length) {
    totalEl.textContent = "-";
    avgEl.textContent = "-";
    peakEl.textContent = "-";
    return;
  }

  const total = values.reduce((a, b) => a + b, 0);
  const avg = total / values.length;
  let peakIdx = 0;
  values.forEach((v, i) => {
    if (v > values[peakIdx]) peakIdx = i;
  });
  const peakLabel = buckets[peakIdx] ? buckets[peakIdx].label || buckets[peakIdx].date : "-";

  totalEl.textContent = `${symbol}${total.toFixed(2)}`;
  avgEl.textContent = `${symbol}${avg.toFixed(2)}`;
  peakEl.textContent = `${symbol}${values[peakIdx].toFixed(2)} (${peakLabel})`;
}

/**
 * Fetch per-category totals for the current month and render the histogram.
 * Safe to call standalone; handles its own errors.
 */
async function loadCategoryChart() {
  const studentId = getActiveStudentId();
  if (!studentId) return;
  if (typeof Chart === "undefined") return; // loadTrends() already reports CDN failure.
  if (!document.getElementById("category-chart")) return;

  const errEl = document.getElementById("category-error");
  if (errEl) {
    errEl.style.display = "none";
    errEl.textContent = "";
  }

  try {
    const res = await fetch(`${getApiBase()}/api/analytics/${studentId}/by-category`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const breakdown = await res.json();
    renderCategoryChart(Array.isArray(breakdown) ? breakdown : []);
  } catch (err) {
    console.error("Error loading category chart:", err);
    if (errEl) {
      errEl.textContent = "Could not load per-category data. Please try again.";
      errEl.style.display = "block";
    }
  }
}

function renderCategoryChart(breakdown) {
  const canvas = document.getElementById("category-chart");
  const emptyEl = document.getElementById("category-empty");
  const countBadge = document.getElementById("category-count-badge");
  if (!canvas) return;

  const symbol = getCurrencySymbol();
  const labels = breakdown.map((b) => b.category);
  const values = breakdown.map((b) => Number(b.amount) || 0);

  if (countBadge) {
    countBadge.textContent = `${breakdown.length} ${breakdown.length === 1 ? "Category" : "Categories"}`;
  }
  if (emptyEl) emptyEl.style.display = breakdown.length ? "none" : "block";

  if (categoryChart) {
    categoryChart.destroy();
    categoryChart = null;
  }
  if (!breakdown.length) return;

  const backgroundColors = labels.map((_, i) => CATEGORY_PALETTE[i % CATEGORY_PALETTE.length]);

  categoryChart = new Chart(canvas.getContext("2d"), {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          label: "Spent",
          data: values,
          backgroundColor: backgroundColors,
          borderColor: backgroundColors,
          borderWidth: 1,
          borderRadius: 6,
          maxBarThickness: 56,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => {
              const item = breakdown[ctx.dataIndex] || {};
              const pct = item.percentage !== undefined ? ` (${item.percentage}%)` : "";
              return ` ${symbol}${Number(ctx.parsed.y).toFixed(2)}${pct}`;
            },
          },
        },
      },
      scales: {
        x: {
          ticks: { maxRotation: 45, minRotation: 0, autoSkip: false },
          grid: { display: false },
        },
        y: {
          beginAtZero: true,
          ticks: {
            callback: (v) => `${symbol}${v}`,
          },
        },
      },
    },
  });
}

// Expose for inline onclick handlers and app.js tab switching.
window.switchTrendRange = switchTrendRange;
window.loadTrends = loadTrends;
window.loadCategoryChart = loadCategoryChart;
window.refreshTrendCharts = function refreshTrendCharts(range) {
  loadTrends(range);
};
