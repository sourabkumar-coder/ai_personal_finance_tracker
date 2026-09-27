const API_BASE = 'http://localhost:8000/api';

// Helper to handle API responses
const handleResponse = async (res) => {
  if (!res.ok) {
    let err = 'An error occurred';
    try {
      const data = await res.json();
      err = data.detail || err;
    } catch {
      err = res.statusText || err;
    }
    throw new Error(err);
  }
  // 204 No Content has no body
  if (res.status === 204) return null;
  return res.json();
};

export const api = {
  // Onboarding & Profile
  register: (data) =>
    fetch(`${API_BASE}/onboarding/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }).then(handleResponse),

  getProfile: (studentId) =>
    fetch(`${API_BASE}/onboarding/profile/${studentId}`).then(handleResponse),

  getProfileByEmail: (email) =>
    fetch(`${API_BASE}/onboarding/profile/by-email/${encodeURIComponent(email)}`).then(handleResponse),

  listStudents: (skip = 0, limit = 50) =>
    fetch(`${API_BASE}/onboarding/students?skip=${skip}&limit=${limit}`).then(handleResponse),

  updateProfile: (studentId, data) =>
    fetch(`${API_BASE}/onboarding/profile/${studentId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }).then(handleResponse),

  deleteProfile: (studentId) =>
    fetch(`${API_BASE}/onboarding/profile/${studentId}`, {
      method: 'DELETE',
    }).then(handleResponse),

  seedDemo: () =>
    fetch(`${API_BASE}/onboarding/seed-demo`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    }).then(handleResponse),

  // Expenses
  getExpenses: (studentId, filters = {}) => {
    const params = new URLSearchParams();
    if (filters.category) params.append('category', filters.category);
    if (filters.startDate) params.append('start_date', filters.startDate);
    if (filters.endDate) params.append('end_date', filters.endDate);
    if (filters.paymentMethod) params.append('payment_method', filters.paymentMethod);
    const qs = params.toString() ? `?${params.toString()}` : '';
    return fetch(`${API_BASE}/expenses/${studentId}${qs}`).then(handleResponse);
  },

  addExpense: (data) =>
    fetch(`${API_BASE}/expenses/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }).then(handleResponse),

  updateExpense: (expenseId, data) =>
    fetch(`${API_BASE}/expenses/${expenseId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }).then(handleResponse),

  deleteExpense: (expenseId) =>
    fetch(`${API_BASE}/expenses/${expenseId}`, {
      method: 'DELETE',
    }).then(handleResponse),

  // Budgets
  getBudgets: (studentId) =>
    fetch(`${API_BASE}/budgets/${studentId}`).then(handleResponse),

  getBudgetStatuses: (studentId, year = null, month = null) => {
    const params = new URLSearchParams();
    if (year) params.append('year', year);
    if (month) params.append('month', month);
    const qs = params.toString() ? `?${params.toString()}` : '';
    return fetch(`${API_BASE}/budgets/${studentId}/status${qs}`).then(handleResponse);
  },

  setBudget: (data) =>
    fetch(`${API_BASE}/budgets/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }).then(handleResponse),

  deleteBudget: (budgetId) =>
    fetch(`${API_BASE}/budgets/${budgetId}`, {
      method: 'DELETE',
    }).then(handleResponse),

  // Goals
  getGoals: (studentId) =>
    fetch(`${API_BASE}/goals/${studentId}`).then(handleResponse),

  addGoal: (data) =>
    fetch(`${API_BASE}/goals/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }).then(handleResponse),

  depositToGoal: (goalId, amount) =>
    fetch(`${API_BASE}/goals/${goalId}/deposit`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ amount: parseFloat(amount) }),
    }).then(handleResponse),

  updateGoal: (goalId, data) =>
    fetch(`${API_BASE}/goals/${goalId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }).then(handleResponse),

  deleteGoal: (goalId) =>
    fetch(`${API_BASE}/goals/${goalId}`, {
      method: 'DELETE',
    }).then(handleResponse),

  // Analytics
  getAnalyticsOverview: (studentId, year = null, month = null) => {
    const params = new URLSearchParams();
    if (year) params.append('year', year);
    if (month) params.append('month', month);
    const qs = params.toString() ? `?${params.toString()}` : '';
    return fetch(`${API_BASE}/analytics/${studentId}/overview${qs}`).then(handleResponse);
  },

  getCategoryBreakdown: (studentId, year = null, month = null) => {
    const params = new URLSearchParams();
    if (year) params.append('year', year);
    if (month) params.append('month', month);
    const qs = params.toString() ? `?${params.toString()}` : '';
    return fetch(`${API_BASE}/analytics/${studentId}/by-category${qs}`).then(handleResponse);
  },

  getTrends: (studentId, year = null, month = null) => {
    const params = new URLSearchParams();
    if (year) params.append('year', year);
    if (month) params.append('month', month);
    const qs = params.toString() ? `?${params.toString()}` : '';
    return fetch(`${API_BASE}/analytics/${studentId}/trends${qs}`).then(handleResponse);
  },

  // AI & Recommendations
  getRecommendations: (studentId, unreadOnly = false) =>
    fetch(`${API_BASE}/recommendations/${studentId}?unread_only=${unreadOnly}`).then(handleResponse),

  generateRecommendations: (studentId) =>
    fetch(`${API_BASE}/recommendations/${studentId}/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    }).then(handleResponse),

  getForecast: (studentId) =>
    fetch(`${API_BASE}/recommendations/${studentId}/forecast`).then(handleResponse),

  markRecommendationRead: (recId) =>
    fetch(`${API_BASE}/recommendations/${recId}/read`, {
      method: 'PATCH',
    }).then(handleResponse),

  markAllRecommendationsRead: (studentId) =>
    fetch(`${API_BASE}/recommendations/${studentId}/read-all`, {
      method: 'PATCH',
    }).then(handleResponse),

  deleteRecommendation: (recId) =>
    fetch(`${API_BASE}/recommendations/${recId}`, {
      method: 'DELETE',
    }).then(handleResponse),
};

