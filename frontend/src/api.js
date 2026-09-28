const API_BASE =
  (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_API_URL
    ? import.meta.env.VITE_API_URL
    : null)
  || (typeof window !== 'undefined' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
    ? 'http://localhost:8000/api'
    : 'https://ai-personal-finance-tracker-7qp8.onrender.com/api');

const TOKEN_KEY = 'authToken';

export const getToken = () => {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
};

export const setToken = (token) => {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    // storage unavailable (private mode) — requests simply go unauthenticated
  }
};

export const clearAuthStorage = () => {
  try {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem('student_id');
  } catch {
    // ignore
  }
};

// Authenticated request helper: attaches Bearer token and bounces to
// onboarding when the backend reports the session as unauthorized.
async function request(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  const token = getToken();
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (res.status === 401) {
    clearAuthStorage();
    if (typeof window !== 'undefined' && window.location.pathname !== '/onboarding') {
      window.location.href = '/onboarding';
    }
  }
  return res;
}

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
  // Auth (public — no token needed yet)
  authRegister: (data) =>
    request('/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }).then(handleResponse),

  authLogin: (email, password) =>
    request('/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ username: email, password }),
    }).then(handleResponse),

  getMe: () =>
    request('/auth/me').then(handleResponse),

  // Onboarding & Profile
  getProfile: (studentId) =>
    request(`/onboarding/profile/${studentId}`).then(handleResponse),

  getProfileByEmail: (email) =>
    request(`/onboarding/profile/by-email/${encodeURIComponent(email)}`).then(handleResponse),

  listStudents: (skip = 0, limit = 50) =>
    request(`/onboarding/students?skip=${skip}&limit=${limit}`).then(handleResponse),

  updateProfile: (studentId, data) =>
    request(`/onboarding/profile/${studentId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }).then(handleResponse),

  deleteProfile: (studentId) =>
    request(`/onboarding/profile/${studentId}`, {
      method: 'DELETE',
    }).then(handleResponse),

  // Expenses
  getExpenses: (studentId, filters = {}) => {
    const params = new URLSearchParams();
    if (filters.category) params.append('category', filters.category);
    if (filters.startDate) params.append('start_date', filters.startDate);
    if (filters.endDate) params.append('end_date', filters.endDate);
    if (filters.paymentMethod) params.append('payment_method', filters.paymentMethod);
    const qs = params.toString() ? `?${params.toString()}` : '';
    return request(`/expenses/${studentId}${qs}`).then(handleResponse);
  },

  addExpense: (data) =>
    request('/expenses/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }).then(handleResponse),

  updateExpense: (expenseId, data) =>
    request(`/expenses/${expenseId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }).then(handleResponse),

  deleteExpense: (expenseId) =>
    request(`/expenses/${expenseId}`, {
      method: 'DELETE',
    }).then(handleResponse),

  // Budgets
  getBudgets: (studentId) =>
    request(`/budgets/${studentId}`).then(handleResponse),

  getBudgetStatuses: (studentId, year = null, month = null) => {
    const params = new URLSearchParams();
    if (year) params.append('year', year);
    if (month) params.append('month', month);
    const qs = params.toString() ? `?${params.toString()}` : '';
    return request(`/budgets/${studentId}/status${qs}`).then(handleResponse);
  },

  setBudget: (data) =>
    request('/budgets/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }).then(handleResponse),

  deleteBudget: (budgetId) =>
    request(`/budgets/${budgetId}`, {
      method: 'DELETE',
    }).then(handleResponse),

  // Goals
  getGoals: (studentId) =>
    request(`/goals/${studentId}`).then(handleResponse),

  addGoal: (data) =>
    request('/goals/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }).then(handleResponse),

  depositToGoal: (goalId, amount) =>
    request(`/goals/${goalId}/deposit`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ amount: parseFloat(amount) }),
    }).then(handleResponse),

  updateGoal: (goalId, data) =>
    request(`/goals/${goalId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }).then(handleResponse),

  deleteGoal: (goalId) =>
    request(`/goals/${goalId}`, {
      method: 'DELETE',
    }).then(handleResponse),

  // Analytics
  getAnalyticsOverview: (studentId, year = null, month = null) => {
    const params = new URLSearchParams();
    if (year) params.append('year', year);
    if (month) params.append('month', month);
    const qs = params.toString() ? `?${params.toString()}` : '';
    return request(`/analytics/${studentId}/overview${qs}`).then(handleResponse);
  },

  getCategoryBreakdown: (studentId, year = null, month = null) => {
    const params = new URLSearchParams();
    if (year) params.append('year', year);
    if (month) params.append('month', month);
    const qs = params.toString() ? `?${params.toString()}` : '';
    return request(`/analytics/${studentId}/by-category${qs}`).then(handleResponse);
  },

  getTrends: (studentId, year = null, month = null) => {
    const params = new URLSearchParams();
    if (year) params.append('year', year);
    if (month) params.append('month', month);
    const qs = params.toString() ? `?${params.toString()}` : '';
    return request(`/analytics/${studentId}/trends${qs}`).then(handleResponse);
  },

  // AI & Recommendations
  getRecommendations: (studentId, unreadOnly = false) =>
    request(`/recommendations/${studentId}?unread_only=${unreadOnly}`).then(handleResponse),

  generateRecommendations: (studentId) =>
    request(`/recommendations/${studentId}/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    }).then(handleResponse),

  getForecast: (studentId) =>
    request(`/recommendations/${studentId}/forecast`).then(handleResponse),

  markRecommendationRead: (recId) =>
    request(`/recommendations/${recId}/read`, {
      method: 'PATCH',
    }).then(handleResponse),

  markAllRecommendationsRead: (studentId) =>
    request(`/recommendations/${studentId}/read-all`, {
      method: 'PATCH',
    }).then(handleResponse),

  deleteRecommendation: (recId) =>
    request(`/recommendations/${recId}`, {
      method: 'DELETE',
    }).then(handleResponse),
};
