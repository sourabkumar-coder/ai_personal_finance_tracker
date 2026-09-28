import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';
import { useAuth } from '../auth';
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip as RechartsTooltip,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  BarChart,
  Bar,
} from 'recharts';
import {
  TrendingUp,
  AlertCircle,
  Plus,
  LogOut,
  Loader2,
  X,
  Wallet,
  Target,
  CreditCard,
  Trash2,
  RefreshCw,
  Sparkles,
  ChevronRight,
  Filter,
  CheckCircle2,
  AlertTriangle,
  Search,
  BarChart3,
  PiggyBank,
  ShieldCheck,
  Clock,
  Menu,
} from 'lucide-react';

const CHART_COLORS = [
  '#4F46E5', // Indigo
  '#10B981', // Emerald
  '#F59E0B', // Amber
  '#EF4444', // Rose
  '#8B5CF6', // Violet
  '#06B6D4', // Cyan
  '#EC4899', // Pink
  '#64748B', // Slate
];

const CATEGORY_ICONS = {
  Food: '🍔',
  Books: '📚',
  Transport: '🚌',
  Entertainment: '🎬',
  Fitness: '🏋️',
  Utilities: '💡',
  Shopping: '🛍️',
  General: '🏷️',
  Other: '📦',
};

const Dashboard = () => {
  const navigate = useNavigate();
  const { logout } = useAuth();
  const studentId = localStorage.getItem('student_id');
  const toastIdRef = useRef(0);

  // Navigation tab
  const [activeTab, setActiveTab] = useState('overview'); // overview, expenses, budgets, goals, trends, advisor
  const [sidebarOpen, setSidebarOpen] = useState(false); // mobile drawer

  // Switch tab and close the mobile drawer
  const goTab = (tab) => {
    setActiveTab(tab);
    setSidebarOpen(false);
  };

  // Global loading
  const [loading, setLoading] = useState(true);
  const [aiGenerating, setAiGenerating] = useState(false);

  // App Data
  const [profile, setProfile] = useState(null);
  const [expenses, setExpenses] = useState([]);
  const [budgetStatuses, setBudgetStatuses] = useState([]);
  const [goals, setGoals] = useState([]);
  const [recommendations, setRecommendations] = useState([]);
  const [overview, setOverview] = useState(null);
  const [trends, setTrends] = useState([]);
  const [forecast, setForecast] = useState(null);
  const [categoryBreakdown, setCategoryBreakdown] = useState([]);

  // Toast notifications
  const [toasts, setToasts] = useState([]);
  const addToast = (message, type = 'success') => {
    toastIdRef.current += 1;
    const id = toastIdRef.current;
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 4000);
  };

  // Modals state
  const [isExpenseModalOpen, setExpenseModalOpen] = useState(false);
  const [isBudgetModalOpen, setBudgetModalOpen] = useState(false);
  const [isGoalModalOpen, setGoalModalOpen] = useState(false);
  const [isDepositModalOpen, setDepositModalOpen] = useState(false);
  const [selectedGoalForDeposit, setSelectedGoalForDeposit] = useState(null);

  // Expense form state
  const [expenseForm, setExpenseForm] = useState({
    title: '',
    amount: '',
    category: 'Food',
    payment_method: 'UPI',
    date: new Date().toISOString().split('T')[0],
    notes: '',
  });

  // Budget form state
  const [budgetForm, setBudgetForm] = useState({
    category: 'Food',
    monthly_limit: '',
  });

  // Goal form state
  const [goalForm, setGoalForm] = useState({
    title: '',
    target_amount: '',
    current_amount: '0',
    deadline: '',
  });

  // Deposit form state
  const [depositAmount, setDepositAmount] = useState('');

  // Expenses Tab Filters
  const [filterSearch, setFilterSearch] = useState('');
  const [filterCategory, setFilterCategory] = useState('');
  const [filterPayment, setFilterPayment] = useState('');

  // AI Advisor filter
  const [recFilterImpact, setRecFilterImpact] = useState('ALL'); // ALL, High, Medium, Low

  const handleLogout = useCallback(() => {
    logout();
    navigate('/onboarding');
  }, [navigate, logout]);

  // Main Data Fetcher
  const fetchAllData = useCallback(async () => {
    if (!studentId) return;

    try {
      const results = await Promise.allSettled([
        api.getProfile(studentId),
        api.getExpenses(studentId),
        api.getBudgetStatuses(studentId),
        api.getGoals(studentId),
        api.getRecommendations(studentId),
        api.getAnalyticsOverview(studentId),
        api.getTrends(studentId),
        api.getForecast(studentId),
        api.getCategoryBreakdown(studentId),
      ]);

      const [
        profileRes,
        expensesRes,
        budgetsRes,
        goalsRes,
        recsRes,
        overviewRes,
        trendsRes,
        forecastRes,
        breakdownRes,
      ] = results;

      if (profileRes.status === 'fulfilled') {
        setProfile(profileRes.value);
      } else {
        console.error('Failed to load profile:', profileRes.reason);
        handleLogout();
        return;
      }

      if (expensesRes.status === 'fulfilled') setExpenses(expensesRes.value || []);
      if (budgetsRes.status === 'fulfilled') setBudgetStatuses(budgetsRes.value || []);
      if (goalsRes.status === 'fulfilled') setGoals(goalsRes.value || []);
      if (recsRes.status === 'fulfilled') setRecommendations(recsRes.value || []);
      if (overviewRes.status === 'fulfilled') setOverview(overviewRes.value || null);
      if (trendsRes.status === 'fulfilled') setTrends(trendsRes.value || []);
      if (forecastRes.status === 'fulfilled') setForecast(forecastRes.value || null);
      if (breakdownRes.status === 'fulfilled') setCategoryBreakdown(breakdownRes.value || []);
    } catch (err) {
      console.error('Unexpected fetch error:', err);
    } finally {
      setLoading(false);
    }
  }, [studentId, handleLogout]);

  useEffect(() => {
    if (!studentId) {
      navigate('/onboarding');
      return;
    }
    let isCancelled = false;
    Promise.resolve().then(() => {
      if (!isCancelled) {
        fetchAllData();
      }
    });
    return () => {
      isCancelled = true;
    };
  }, [studentId, navigate, fetchAllData]);

  // Add Expense
  const handleAddExpense = async (e) => {
    e.preventDefault();
    if (!expenseForm.title.trim() || !expenseForm.amount) return;

    try {
      await api.addExpense({
        student_id: parseInt(studentId),
        title: expenseForm.title.trim(),
        amount: parseFloat(expenseForm.amount),
        category: expenseForm.category,
        payment_method: expenseForm.payment_method,
        date: expenseForm.date,
        notes: expenseForm.notes ? expenseForm.notes.trim() : null,
      });

      setExpenseModalOpen(false);
      setExpenseForm({
        title: '',
        amount: '',
        category: 'Food',
        payment_method: 'UPI',
        date: new Date().toISOString().split('T')[0],
        notes: '',
      });
      addToast('Expense recorded successfully!');
      fetchAllData();
    } catch (err) {
      addToast('Failed to add expense: ' + err.message, 'error');
    }
  };

  // Delete Expense
  const handleDeleteExpense = async (expenseId) => {
    if (!window.confirm('Delete this expense?')) return;
    try {
      await api.deleteExpense(expenseId);
      addToast('Expense deleted.');
      fetchAllData();
    } catch (err) {
      addToast('Failed to delete expense: ' + err.message, 'error');
    }
  };

  // Set / Update Budget
  const handleSetBudget = async (e) => {
    e.preventDefault();
    if (!budgetForm.monthly_limit) return;
    const now = new Date();

    try {
      await api.setBudget({
        student_id: parseInt(studentId),
        category: budgetForm.category.trim(),
        monthly_limit: parseFloat(budgetForm.monthly_limit),
        month: now.getMonth() + 1,
        year: now.getFullYear(),
      });

      setBudgetModalOpen(false);
      setBudgetForm({ category: 'Food', monthly_limit: '' });
      addToast(`Budget set for ${budgetForm.category}!`);
      fetchAllData();
    } catch (err) {
      addToast('Failed to set budget: ' + err.message, 'error');
    }
  };

  // Delete Budget
  const handleDeleteBudget = async (budgetId) => {
    if (!window.confirm('Delete this budget limit?')) return;
    try {
      await api.deleteBudget(budgetId);
      addToast('Budget limit removed.');
      fetchAllData();
    } catch (err) {
      addToast('Failed to delete budget: ' + err.message, 'error');
    }
  };

  // Create Goal
  const handleCreateGoal = async (e) => {
    e.preventDefault();
    if (!goalForm.title.trim() || !goalForm.target_amount || !goalForm.deadline) return;

    try {
      await api.addGoal({
        student_id: parseInt(studentId),
        title: goalForm.title.trim(),
        target_amount: parseFloat(goalForm.target_amount),
        current_amount: parseFloat(goalForm.current_amount) || 0.0,
        deadline: goalForm.deadline,
      });

      setGoalModalOpen(false);
      setGoalForm({ title: '', target_amount: '', current_amount: '0', deadline: '' });
      addToast(`Savings goal '${goalForm.title}' created!`);
      fetchAllData();
    } catch (err) {
      addToast('Failed to create goal: ' + err.message, 'error');
    }
  };

  // Deposit to Goal
  const handleDepositToGoal = async (e) => {
    e.preventDefault();
    if (!selectedGoalForDeposit || !depositAmount || parseFloat(depositAmount) <= 0) return;

    try {
      await api.depositToGoal(selectedGoalForDeposit.id, parseFloat(depositAmount));
      setDepositModalOpen(false);
      setDepositAmount('');
      addToast(`Saved $${depositAmount} towards '${selectedGoalForDeposit.title}'! 🎯`);
      fetchAllData();
    } catch (err) {
      addToast('Deposit failed: ' + err.message, 'error');
    }
  };

  // Delete Goal
  const handleDeleteGoal = async (goalId) => {
    if (!window.confirm('Delete this savings goal?')) return;
    try {
      await api.deleteGoal(goalId);
      addToast('Savings goal deleted.');
      fetchAllData();
    } catch (err) {
      addToast('Failed to delete goal: ' + err.message, 'error');
    }
  };

  // Generate AI Recommendations
  const handleGenerateAI = async () => {
    setAiGenerating(true);
    try {
      await api.generateRecommendations(studentId);
      addToast('AI analysis updated with fresh insights! ✨');
      fetchAllData();
    } catch (err) {
      addToast('AI analysis failed: ' + err.message, 'error');
    } finally {
      setAiGenerating(false);
    }
  };

  // Dismiss / Mark Read Recommendation
  const handleMarkRecRead = async (recId) => {
    try {
      await api.markRecommendationRead(recId);
      setRecommendations(prev =>
        prev.map(r => (r.id === recId ? { ...r, is_read: true } : r))
      );
    } catch {
      // ignore
    }
  };

  const handleDeleteRec = async (recId) => {
    try {
      await api.deleteRecommendation(recId);
      setRecommendations(prev => prev.filter(r => r.id !== recId));
      addToast('Insight dismissed.');
    } catch (err) {
      addToast('Failed to dismiss insight: ' + err.message, 'error');
    }
  };

  const handleMarkAllRecsRead = async () => {
    try {
      await api.markAllRecommendationsRead(studentId);
      setRecommendations(prev => prev.map(r => ({ ...r, is_read: true })));
      addToast('All insights marked as read.');
    } catch (err) {
      addToast('Failed: ' + err.message, 'error');
    }
  };

  // Filtered Expenses
  const filteredExpenses = useMemo(() => {
    return expenses.filter(exp => {
      const matchSearch =
        !filterSearch ||
        exp.title.toLowerCase().includes(filterSearch.toLowerCase()) ||
        (exp.notes && exp.notes.toLowerCase().includes(filterSearch.toLowerCase()));
      const matchCategory =
        !filterCategory || exp.category.toLowerCase() === filterCategory.toLowerCase();
      const matchPayment =
        !filterPayment || exp.payment_method.toLowerCase() === filterPayment.toLowerCase();
      return matchSearch && matchCategory && matchPayment;
    });
  }, [expenses, filterSearch, filterCategory, filterPayment]);

  // Filtered Recommendations
  const filteredRecs = useMemo(() => {
    if (recFilterImpact === 'ALL') return recommendations;
    return recommendations.filter(
      r => r.impact_level && r.impact_level.toUpperCase() === recFilterImpact.toUpperCase()
    );
  }, [recommendations, recFilterImpact]);

  // Derived financial numbers
  const totalSpent = expenses.reduce((sum, e) => sum + e.amount, 0);
  const allowance = profile?.monthly_allowance || 0;
  const safeToSpend = Math.max(0, allowance - totalSpent);
  const savingsRate = allowance > 0 ? Math.max(0, ((safeToSpend / allowance) * 100).toFixed(1)) : '0.0';

  // Pie chart data
  const pieChartData = useMemo(() => {
    if (categoryBreakdown.length > 0) {
      return categoryBreakdown.map((item, idx) => ({
        name: item.category,
        value: item.amount,
        color: CHART_COLORS[idx % CHART_COLORS.length],
        percentage: item.percentage,
      }));
    }
    // Fallback if breakdown not returned yet
    const catMap = {};
    expenses.forEach(e => {
      catMap[e.category] = (catMap[e.category] || 0) + e.amount;
    });
    return Object.keys(catMap).map((cat, idx) => ({
      name: cat,
      value: catMap[cat],
      color: CHART_COLORS[idx % CHART_COLORS.length],
      percentage: totalSpent > 0 ? Math.round((catMap[cat] / totalSpent) * 100) : 0,
    }));
  }, [categoryBreakdown, expenses, totalSpent]);

  // Initial Loading state
  if (loading) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', backgroundColor: 'var(--bg-app)', gap: '1rem' }}>
        <Loader2 className="animate-spin text-primary" size={48} />
        <p style={{ color: 'var(--text-secondary)', fontWeight: 500, fontSize: '0.9375rem' }}>
          Loading your financial workspace...
        </p>
      </div>
    );
  }

  const currencySymbol = profile?.currency === 'INR' ? '₹' : profile?.currency === 'EUR' ? '€' : profile?.currency === 'GBP' ? '£' : '$';

  return (
    <div className="app-shell">
      {/* Toast Notifications */}
      <div className="toast-container">
        {toasts.map(t => (
          <div key={t.id} className={`toast toast-${t.type}`}>
            {t.type === 'success' && <CheckCircle2 size={18} className="text-success" />}
            {t.type === 'error' && <AlertCircle size={18} className="text-danger" />}
            {t.type === 'info' && <Sparkles size={18} className="text-primary" />}
            <span>{t.message}</span>
          </div>
        ))}
      </div>

      {/* Sidebar Navigation */}
      {sidebarOpen && (
        <div
          className="sidebar-backdrop"
          onClick={() => setSidebarOpen(false)}
          aria-hidden="true"
        />
      )}
      <aside className={`sidebar${sidebarOpen ? ' open' : ''}`}>
        <div className="brand-section">
          <div className="brand-logo-icon">💎</div>
          <div className="brand-meta">
            <h2>SmartFinance</h2>
            <span className="brand-badge">
              <Sparkles size={10} /> Gemini AI Powered
            </span>
          </div>
        </div>

        <nav className="sidebar-nav">
          <span className="nav-heading">Menu</span>
          
          <button
            type="button"
            className={`sidebar-btn ${activeTab === 'overview' ? 'active' : ''}`}
            onClick={() => goTab('overview')}
          >
            <div className="sidebar-btn-content">
              <BarChart3 size={18} />
              <span>Overview</span>
            </div>
            <ChevronRight size={14} style={{ opacity: activeTab === 'overview' ? 1 : 0.4 }} />
          </button>

          <button
            type="button"
            className={`sidebar-btn ${activeTab === 'expenses' ? 'active' : ''}`}
            onClick={() => goTab('expenses')}
          >
            <div className="sidebar-btn-content">
              <CreditCard size={18} />
              <span>Expenses</span>
            </div>
            <span className="badge badge-subtle" style={{ fontSize: '0.7rem', padding: '0.1rem 0.4rem' }}>
              {expenses.length}
            </span>
          </button>

          <button
            type="button"
            className={`sidebar-btn ${activeTab === 'budgets' ? 'active' : ''}`}
            onClick={() => goTab('budgets')}
          >
            <div className="sidebar-btn-content">
              <Target size={18} />
              <span>Budgets</span>
            </div>
            {budgetStatuses.some(b => b.status === 'Exceeded' || b.status === 'Warning') && (
              <AlertTriangle size={14} className="text-warning" />
            )}
          </button>

          <button
            type="button"
            className={`sidebar-btn ${activeTab === 'goals' ? 'active' : ''}`}
            onClick={() => goTab('goals')}
          >
            <div className="sidebar-btn-content">
              <PiggyBank size={18} />
              <span>Savings Goals</span>
            </div>
            <span className="badge badge-subtle" style={{ fontSize: '0.7rem', padding: '0.1rem 0.4rem' }}>
              {goals.length}
            </span>
          </button>

          <button
            type="button"
            className={`sidebar-btn ${activeTab === 'trends' ? 'active' : ''}`}
            onClick={() => goTab('trends')}
          >
            <div className="sidebar-btn-content">
              <TrendingUp size={18} />
              <span>Trends & Forecast</span>
            </div>
            {forecast?.health_status && (
              <span className={`badge ${forecast.health_status === 'Healthy' ? 'badge-success' : 'badge-danger'}`} style={{ fontSize: '0.65rem' }}>
                {forecast.health_status}
              </span>
            )}
          </button>

          <span className="nav-heading" style={{ marginTop: '1rem' }}>Intelligence</span>

          <button
            type="button"
            className={`sidebar-btn ${activeTab === 'advisor' ? 'active' : ''}`}
            onClick={() => goTab('advisor')}
          >
            <div className="sidebar-btn-content">
              <Sparkles size={18} style={{ color: '#A78BFA' }} />
              <span>AI Advisor</span>
            </div>
            {recommendations.filter(r => !r.is_read).length > 0 && (
              <span className="badge badge-danger" style={{ fontSize: '0.68rem', padding: '0.1rem 0.45rem' }}>
                {recommendations.filter(r => !r.is_read).length} new
              </span>
            )}
          </button>
        </nav>

        {/* Sidebar User Profile Card */}
        <div className="sidebar-user-card">
          <div className="user-avatar-circle">
            {profile?.name ? profile.name.slice(0, 2).toUpperCase() : 'U'}
          </div>
          <div className="user-info-text">
            <h4>{profile?.name || 'Student'}</h4>
            <p>{profile?.college_year || 'College'} • {currencySymbol}{allowance}/mo</p>
          </div>
          <button
            type="button"
            className="btn btn-outline btn-icon"
            onClick={handleLogout}
            title="Log Out of My Account"
            style={{ width: '32px', height: '32px', color: '#CBD5E1', borderColor: 'rgba(255,255,255,0.2)' }}
          >
            <LogOut size={15} />
          </button>
        </div>
      </aside>

      {/* Main Viewport */}
      <div className="main-viewport">
        {/* Top Header */}
        <header className="top-header">
          <div className="header-left">
            <button
              type="button"
              className="btn btn-outline btn-icon hamburger-btn"
              onClick={() => setSidebarOpen(true)}
              aria-label="Open navigation menu"
            >
              <Menu size={20} />
            </button>
            <div className="header-title-block">
              <h1>
                {activeTab === 'overview' && 'Financial Overview'}
                {activeTab === 'expenses' && 'Expense Ledger'}
                {activeTab === 'budgets' && 'Category Budgets'}
                {activeTab === 'goals' && 'Savings Goals & Milestones'}
                {activeTab === 'trends' && 'Spending Velocity & Predictions'}
                {activeTab === 'advisor' && 'AI Financial Advisor'}
              </h1>
              <p>
                {overview?.period || `${new Date().toLocaleString('default', { month: 'long', year: 'numeric' })}`} • Real-time Sync
              </p>
            </div>
          </div>

          <div className="header-actions">
            <div className="ai-status-pill">
              <span className="status-dot"></span>
              <span>Gemini Engine Ready</span>
            </div>

            <button
              type="button"
              className="btn btn-primary btn-sm"
              onClick={() => setExpenseModalOpen(true)}
            >
              <Plus size={16} /> New Expense
            </button>

            <button
              type="button"
              className="btn btn-outline btn-icon"
              onClick={handleLogout}
              title="Log out"
            >
              <LogOut size={16} />
            </button>
          </div>
        </header>

        {/* Dynamic Tab Content Area */}
        <main className="content-area">
          
          {/* ========================================================================= */}
          {/* TAB 1: OVERVIEW */}
          {/* ========================================================================= */}
          {activeTab === 'overview' && (
            <>
              {/* 4 KPI Metric Cards */}
              <div className="metrics-grid">
                <div className="metric-card card-indigo">
                  <div className="metric-header">
                    <span className="metric-title">Monthly Allowance</span>
                    <div className="metric-icon-wrap indigo">
                      <Wallet size={18} />
                    </div>
                  </div>
                  <div className="metric-value">{currencySymbol}{allowance.toFixed(2)}</div>
                  <div className="metric-sub">
                    <span>Base student stipend / income</span>
                  </div>
                </div>

                <div className="metric-card card-rose">
                  <div className="metric-header">
                    <span className="metric-title">Total Spent</span>
                    <div className="metric-icon-wrap rose">
                      <TrendingUp size={18} />
                    </div>
                  </div>
                  <div className="metric-value text-danger">{currencySymbol}{totalSpent.toFixed(2)}</div>
                  <div className="metric-sub">
                    <span>{expenses.length} transaction{expenses.length === 1 ? '' : 's'} this month</span>
                  </div>
                </div>

                <div className="metric-card card-emerald">
                  <div className="metric-header">
                    <span className="metric-title">Safe To Spend</span>
                    <div className="metric-icon-wrap emerald">
                      <ShieldCheck size={18} />
                    </div>
                  </div>
                  <div className="metric-value text-success">{currencySymbol}{safeToSpend.toFixed(2)}</div>
                  <div className="metric-sub">
                    <span>{safeToSpend > 0 ? `Savings Rate: ${savingsRate}%` : 'Exceeded monthly budget'}</span>
                  </div>
                </div>

                <div className="metric-card card-amber">
                  <div className="metric-header">
                    <span className="metric-title">Month-End Health</span>
                    <div className="metric-icon-wrap amber">
                      <AlertCircle size={18} />
                    </div>
                  </div>
                  <div className="metric-value" style={{ fontSize: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span className={`badge ${forecast?.health_status === 'Healthy' ? 'badge-success' : forecast?.health_status === 'Caution' ? 'badge-warning' : 'badge-danger'}`} style={{ fontSize: '0.85rem' }}>
                      {forecast?.health_status || 'Analyzing'}
                    </span>
                  </div>
                  <div className="metric-sub">
                    <span>Burn Rate: {currencySymbol}{forecast?.daily_burn_rate || '0.00'}/day</span>
                  </div>
                </div>
              </div>

              {/* Quick Actions Bar */}
              <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                <button type="button" className="btn btn-primary" onClick={() => setExpenseModalOpen(true)}>
                  <Plus size={16} /> Log Expense
                </button>
                <button type="button" className="btn btn-outline" onClick={() => setBudgetModalOpen(true)}>
                  <Target size={16} /> Set Category Budget
                </button>
                <button type="button" className="btn btn-outline" onClick={() => setGoalModalOpen(true)}>
                  <PiggyBank size={16} /> New Savings Goal
                </button>
                <button
                  type="button"
                  className="btn btn-ai"
                  onClick={handleGenerateAI}
                  disabled={aiGenerating}
                >
                  {aiGenerating ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />}
                  <span>{aiGenerating ? 'AI Reasoning...' : 'Run AI Analysis'}</span>
                </button>
              </div>

              {/* Grid: Recent Expenses + Charts */}
              <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: '1.5rem' }}>
                
                {/* Left: Recent Expenses */}
                <div className="card">
                  <div className="card-header">
                    <h3>Recent Transactions</h3>
                    <button
                      type="button"
                      className="btn btn-outline btn-sm"
                      onClick={() => goTab('expenses')}
                    >
                      View All <ChevronRight size={14} />
                    </button>
                  </div>
                  
                  {expenses.length === 0 ? (
                    <div className="empty-state">
                      <div className="empty-icon-circle">
                        <CreditCard size={24} />
                      </div>
                      <h4>No expenses logged yet</h4>
                      <p>Start logging your daily purchases to unlock budget alerts and AI advice.</p>
                      <button type="button" className="btn btn-primary btn-sm" onClick={() => setExpenseModalOpen(true)}>
                        <Plus size={16} /> Add First Expense
                      </button>
                    </div>
                  ) : (
                    <div className="table-container" style={{ border: 'none' }}>
                      <table className="table">
                        <thead>
                          <tr>
                            <th>Date</th>
                            <th>Description</th>
                            <th>Category</th>
                            <th style={{ textAlign: 'right' }}>Amount</th>
                            <th style={{ textAlign: 'center', width: '50px' }}>Action</th>
                          </tr>
                        </thead>
                        <tbody>
                          {expenses.slice(0, 6).map((exp) => (
                            <tr key={exp.id}>
                              <td className="text-secondary" style={{ fontSize: '0.8125rem' }}>
                                {exp.date}
                              </td>
                              <td>
                                <div style={{ fontWeight: 600 }}>{exp.title}</div>
                                {exp.payment_method && (
                                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                                    {exp.payment_method}
                                  </div>
                                )}
                              </td>
                              <td>
                                <span className="badge badge-subtle">
                                  {CATEGORY_ICONS[exp.category] || '🏷️'} {exp.category}
                                </span>
                              </td>
                              <td style={{ textAlign: 'right', fontWeight: 700 }} className="text-danger">
                                -{currencySymbol}{exp.amount.toFixed(2)}
                              </td>
                              <td style={{ textAlign: 'center' }}>
                                <button
                                  type="button"
                                  onClick={() => handleDeleteExpense(exp.id)}
                                  className="btn btn-outline btn-icon"
                                  style={{ width: '28px', height: '28px', color: 'var(--danger)' }}
                                  title="Delete transaction"
                                >
                                  <Trash2 size={13} />
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>

                {/* Right: Category Distribution Donut Chart */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                  
                  <div className="card">
                    <div className="card-header">
                      <h3>Spending by Category</h3>
                      <span className="badge badge-primary" style={{ fontSize: '0.7rem' }}>
                        Distribution
                      </span>
                    </div>
                    <div className="card-body">
                      {pieChartData.length === 0 ? (
                        <div style={{ textAlign: 'center', padding: '2rem 1rem', color: 'var(--text-muted)' }}>
                          Log expenses to visualize category breakdown
                        </div>
                      ) : (
                        <div>
                          <div style={{ width: '100%', height: '220px' }}>
                            <ResponsiveContainer width="100%" height="100%">
                              <PieChart>
                                <Pie
                                  data={pieChartData}
                                  innerRadius={55}
                                  outerRadius={85}
                                  paddingAngle={3}
                                  dataKey="value"
                                >
                                  {pieChartData.map((entry, index) => (
                                    <Cell key={`cell-${index}`} fill={entry.color} />
                                  ))}
                                </Pie>
                                <RechartsTooltip
                                  formatter={(value) => [`${currencySymbol}${Number(value).toFixed(2)}`, 'Spent']}
                                />
                              </PieChart>
                            </ResponsiveContainer>
                          </div>

                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginTop: '1rem', justifyContent: 'center' }}>
                            {pieChartData.map((item) => (
                              <div
                                key={item.name}
                                style={{
                                  display: 'flex',
                                  alignItems: 'center',
                                  gap: '0.35rem',
                                  fontSize: '0.75rem',
                                  padding: '0.25rem 0.5rem',
                                  borderRadius: 'var(--radius-sm)',
                                  backgroundColor: 'var(--bg-subtle)',
                                }}
                              >
                                <div style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: item.color }}></div>
                                <span style={{ fontWeight: 600 }}>{item.name}</span>
                                <span style={{ color: 'var(--text-muted)' }}>{currencySymbol}{item.value.toFixed(0)}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* AI Advice Snapshot Card */}
                  <div className="card" style={{ borderLeft: '4px solid var(--accent)' }}>
                    <div className="card-header">
                      <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <Sparkles size={16} className="text-primary" /> AI Financial Advisor
                      </h3>
                      <button
                        type="button"
                        className="btn btn-outline btn-sm"
                        onClick={() => goTab('advisor')}
                      >
                        All Advice <ChevronRight size={14} />
                      </button>
                    </div>
                    <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: '0.875rem' }}>
                      {recommendations.length === 0 ? (
                        <div style={{ textAlign: 'center', padding: '1rem' }}>
                          <p style={{ fontSize: '0.8125rem', color: 'var(--text-muted)', marginBottom: '0.75rem' }}>
                            No recommendations generated yet.
                          </p>
                          <button
                            type="button"
                            className="btn btn-ai btn-sm"
                            onClick={handleGenerateAI}
                            disabled={aiGenerating}
                          >
                            {aiGenerating ? <Loader2 size={14} className="animate-spin" /> : 'Run AI Analysis'}
                          </button>
                        </div>
                      ) : (
                        recommendations.slice(0, 2).map((rec) => (
                          <div
                            key={rec.id}
                            style={{
                              padding: '0.875rem 1rem',
                              borderRadius: 'var(--radius-md)',
                              backgroundColor: rec.impact_level === 'High' ? 'var(--danger-light)' : 'var(--primary-light)',
                              border: `1px solid ${rec.impact_level === 'High' ? 'var(--danger-border)' : 'var(--primary-border)'}`,
                            }}
                          >
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                              <h4 style={{ fontSize: '0.875rem', fontWeight: 700, color: 'var(--text-main)' }}>
                                {rec.title}
                              </h4>
                              <span
                                className={`badge ${rec.impact_level === 'High' ? 'badge-danger' : 'badge-primary'}`}
                                style={{ fontSize: '0.65rem' }}
                              >
                                {rec.impact_level} Impact
                              </span>
                            </div>
                            <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
                              {rec.message}
                            </p>
                          </div>
                        ))
                      )}
                    </div>
                  </div>

                </div>
              </div>
            </>
          )}

          {/* ========================================================================= */}
          {/* TAB 2: EXPENSES LEDGER */}
          {/* ========================================================================= */}
          {activeTab === 'expenses' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
              
              {/* Filter Controls Bar */}
              <div className="filter-bar">
                <div className="search-input-wrapper">
                  <Search size={16} />
                  <input
                    type="text"
                    placeholder="Search by title or notes..."
                    value={filterSearch}
                    onChange={(e) => setFilterSearch(e.target.value)}
                    className="input-field"
                  />
                </div>

                <select
                  className="input-field"
                  style={{ width: 'auto', minWidth: '150px' }}
                  value={filterCategory}
                  onChange={(e) => setFilterCategory(e.target.value)}
                >
                  <option value="">All Categories</option>
                  <option value="Food">Food & Dining</option>
                  <option value="Books">Books & Academics</option>
                  <option value="Transport">Transportation</option>
                  <option value="Entertainment">Entertainment</option>
                  <option value="Fitness">Fitness & Health</option>
                  <option value="Utilities">Utilities & Rent</option>
                  <option value="Shopping">Shopping</option>
                  <option value="Other">Other</option>
                </select>

                <select
                  className="input-field"
                  style={{ width: 'auto', minWidth: '150px' }}
                  value={filterPayment}
                  onChange={(e) => setFilterPayment(e.target.value)}
                >
                  <option value="">All Payment Methods</option>
                  <option value="UPI">UPI</option>
                  <option value="Debit Card">Debit Card</option>
                  <option value="Credit Card">Credit Card</option>
                  <option value="Cash">Cash</option>
                  <option value="Online">Online / Net Banking</option>
                </select>

                {(filterSearch || filterCategory || filterPayment) && (
                  <button
                    type="button"
                    className="btn btn-outline btn-sm"
                    onClick={() => {
                      setFilterSearch('');
                      setFilterCategory('');
                      setFilterPayment('');
                    }}
                  >
                    Clear Filters
                  </button>
                )}

                <div style={{ marginLeft: 'auto' }}>
                  <button
                    type="button"
                    className="btn btn-primary btn-sm"
                    onClick={() => setExpenseModalOpen(true)}
                  >
                    <Plus size={16} /> Log Expense
                  </button>
                </div>
              </div>

              {/* Transactions Table */}
              <div className="card">
                <div className="card-header">
                  <h3>All Recorded Expenditures ({filteredExpenses.length})</h3>
                  <span className="badge badge-subtle">
                    Total: {currencySymbol}{filteredExpenses.reduce((s, e) => s + e.amount, 0).toFixed(2)}
                  </span>
                </div>

                {filteredExpenses.length === 0 ? (
                  <div className="empty-state">
                    <div className="empty-icon-circle">
                      <Filter size={24} />
                    </div>
                    <h4>No expenses match your criteria</h4>
                    <p>Try clearing filters or logging a new purchase.</p>
                  </div>
                ) : (
                  <div className="table-container" style={{ border: 'none' }}>
                    <table className="table">
                      <thead>
                        <tr>
                          <th>Date</th>
                          <th>Title / Item</th>
                          <th>Category</th>
                          <th>Payment Method</th>
                          <th>Notes</th>
                          <th style={{ textAlign: 'right' }}>Amount</th>
                          <th style={{ textAlign: 'center', width: '70px' }}>Delete</th>
                        </tr>
                      </thead>
                      <tbody>
                        {filteredExpenses.map((exp) => (
                          <tr key={exp.id}>
                            <td className="text-secondary" style={{ fontSize: '0.8125rem' }}>
                              {exp.date}
                            </td>
                            <td style={{ fontWeight: 600, color: 'var(--text-main)' }}>
                              {exp.title}
                            </td>
                            <td>
                              <span className="badge badge-subtle">
                                {CATEGORY_ICONS[exp.category] || '🏷️'} {exp.category}
                              </span>
                            </td>
                            <td>
                              <span className="badge badge-subtle" style={{ fontSize: '0.75rem' }}>
                                {exp.payment_method}
                              </span>
                            </td>
                            <td style={{ fontSize: '0.8125rem', color: 'var(--text-muted)', maxWidth: '240px' }}>
                              {exp.notes || '—'}
                            </td>
                            <td style={{ textAlign: 'right', fontWeight: 700 }} className="text-danger">
                              -{currencySymbol}{exp.amount.toFixed(2)}
                            </td>
                            <td style={{ textAlign: 'center' }}>
                              <button
                                type="button"
                                className="btn btn-outline btn-icon"
                                style={{ width: '30px', height: '30px', color: 'var(--danger)' }}
                                onClick={() => handleDeleteExpense(exp.id)}
                                title="Delete expense"
                              >
                                <Trash2 size={14} />
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>

            </div>
          )}

          {/* ========================================================================= */}
          {/* TAB 3: BUDGETS */}
          {/* ========================================================================= */}
          {activeTab === 'budgets' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
              
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: '1.25rem', fontWeight: 700 }}>
                    Monthly Category Limits
                  </h2>
                  <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
                    Set spending guardrails. Visual alerts trigger automatically at 80% and 100% threshold.
                  </p>
                </div>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() => setBudgetModalOpen(true)}
                >
                  <Plus size={16} /> Set Category Budget
                </button>
              </div>

              {budgetStatuses.length === 0 ? (
                <div className="empty-state">
                  <div className="empty-icon-circle">
                    <Target size={28} />
                  </div>
                  <h4>No category budgets defined</h4>
                  <p>Establish monthly caps on Dining, Books, Transport, and Entertainment to avoid running out of funds.</p>
                  <button
                    type="button"
                    className="btn btn-primary"
                    onClick={() => setBudgetModalOpen(true)}
                  >
                    <Plus size={16} /> Create First Budget
                  </button>
                </div>
              ) : (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '1.25rem' }}>
                  {budgetStatuses.map((b) => {
                    const isExceeded = b.percentage_used >= 100;
                    const isWarning = b.percentage_used >= 80 && !isExceeded;
                    const statusClass = isExceeded ? 'progress-red' : isWarning ? 'progress-amber' : 'progress-green';
                    const badgeClass = isExceeded ? 'badge-danger' : isWarning ? 'badge-warning' : 'badge-success';

                    return (
                      <div key={b.budget_id} className="card p-4" style={{ display: 'flex', flexDirection: 'column', gap: '1rem', position: 'relative' }}>
                        
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
                            <span style={{ fontSize: '1.5rem' }}>{CATEGORY_ICONS[b.category] || '🎯'}</span>
                            <div>
                              <h3 style={{ fontSize: '1.0625rem', fontWeight: 700, color: 'var(--text-main)' }}>
                                {b.category}
                              </h3>
                              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                                Limit: {currencySymbol}{b.monthly_limit.toFixed(2)}
                              </span>
                            </div>
                          </div>

                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <span className={`badge ${badgeClass}`}>
                              {b.status} ({b.percentage_used.toFixed(0)}%)
                            </span>
                            <button
                              type="button"
                              className="btn btn-outline btn-icon"
                              style={{ width: '28px', height: '28px', color: 'var(--danger)' }}
                              onClick={() => handleDeleteBudget(b.budget_id)}
                              title="Delete budget"
                            >
                              <Trash2 size={13} />
                            </button>
                          </div>
                        </div>

                        {/* Progress bar */}
                        <div className="progress-container">
                          <div className="progress-track">
                            <div
                              className={`progress-fill ${statusClass}`}
                              style={{ width: `${Math.min(100, b.percentage_used)}%` }}
                            ></div>
                          </div>
                        </div>

                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8125rem' }}>
                          <span style={{ color: 'var(--text-secondary)' }}>
                            Spent: <strong>{currencySymbol}{b.total_spent.toFixed(2)}</strong>
                          </span>
                          <span style={{ color: isExceeded ? 'var(--danger)' : 'var(--success)' }}>
                            {isExceeded
                              ? `Over by ${currencySymbol}${(b.total_spent - b.monthly_limit).toFixed(2)}`
                              : `Remaining: ${currencySymbol}${b.remaining.toFixed(2)}`}
                          </span>
                        </div>

                      </div>
                    );
                  })}
                </div>
              )}

            </div>
          )}

          {/* ========================================================================= */}
          {/* TAB 4: SAVINGS GOALS */}
          {/* ========================================================================= */}
          {activeTab === 'goals' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
              
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: '1.25rem', fontWeight: 700 }}>
                    Savings Goals & Targets
                  </h2>
                  <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
                    Save incrementally for semester tuition, tech gear, internships, or trips.
                  </p>
                </div>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() => setGoalModalOpen(true)}
                >
                  <Plus size={16} /> New Goal Target
                </button>
              </div>

              {goals.length === 0 ? (
                <div className="empty-state">
                  <div className="empty-icon-circle">
                    <PiggyBank size={28} />
                  </div>
                  <h4>No savings milestones defined</h4>
                  <p>Set a target amount and deadline to start tracking your savings momentum.</p>
                  <button
                    type="button"
                    className="btn btn-primary"
                    onClick={() => setGoalModalOpen(true)}
                  >
                    <Plus size={16} /> Create First Goal
                  </button>
                </div>
              ) : (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: '1.25rem' }}>
                  {goals.map((g) => {
                    const isAchieved = g.status === 'Achieved' || g.current_amount >= g.target_amount;
                    const pct = Math.min(100, Math.round((g.current_amount / g.target_amount) * 100));

                    return (
                      <div key={g.id} className="card p-6" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between', gap: '1.25rem' }}>
                        
                        <div>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.5rem' }}>
                            <span className={`badge ${isAchieved ? 'badge-success' : 'badge-primary'}`}>
                              {isAchieved ? '🏆 Target Achieved' : 'In Progress'}
                            </span>
                            <button
                              type="button"
                              className="btn btn-outline btn-icon"
                              style={{ width: '28px', height: '28px', color: 'var(--danger)' }}
                              onClick={() => handleDeleteGoal(g.id)}
                              title="Delete goal"
                            >
                              <Trash2 size={13} />
                            </button>
                          </div>

                          <h3 style={{ fontFamily: 'var(--font-heading)', fontSize: '1.125rem', fontWeight: 700, color: 'var(--text-main)', marginBottom: '0.25rem' }}>
                            {g.title}
                          </h3>

                          <div style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                            <Clock size={13} /> Target Date: {g.deadline}
                          </div>
                        </div>

                        {/* Progress Bar & Amount */}
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                            <span style={{ fontSize: '1.35rem', fontWeight: 700, color: 'var(--text-main)' }}>
                              {currencySymbol}{g.current_amount.toFixed(2)}
                            </span>
                            <span style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
                              Goal: {currencySymbol}{g.target_amount.toFixed(2)} ({pct}%)
                            </span>
                          </div>

                          <div className="progress-track" style={{ height: '10px' }}>
                            <div
                              className="progress-fill progress-indigo"
                              style={{ width: `${pct}%` }}
                            ></div>
                          </div>
                        </div>

                        {/* Deposit Action */}
                        <button
                          type="button"
                          className="btn btn-outline w-full"
                          style={{ borderColor: 'var(--primary)', color: 'var(--primary)' }}
                          onClick={() => {
                            setSelectedGoalForDeposit(g);
                            setDepositModalOpen(true);
                          }}
                        >
                          <Plus size={15} /> Deposit Saved Funds
                        </button>

                      </div>
                    );
                  })}
                </div>
              )}

            </div>
          )}

          {/* ========================================================================= */}
          {/* TAB 5: TRENDS & ANALYTICS */}
          {/* ========================================================================= */}
          {activeTab === 'trends' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.75rem' }}>
              
              {/* Daily Spending Trajectory Chart */}
              <div className="card">
                <div className="card-header">
                  <div>
                    <h3>Daily Spending Velocity</h3>
                    <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                      Track day-by-day cash outlays over the current cycle.
                    </p>
                  </div>
                  <span className="badge badge-primary">Current Cycle</span>
                </div>
                <div className="card-body">
                  {trends.length === 0 ? (
                    <div style={{ textAlign: 'center', padding: '3rem 1rem', color: 'var(--text-muted)' }}>
                      No spending data points available yet for this cycle.
                    </div>
                  ) : (
                    <div style={{ width: '100%', height: '280px' }}>
                      <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={trends} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
                          <defs>
                            <linearGradient id="spendGrad" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="5%" stopColor="#4F46E5" stopOpacity={0.4} />
                              <stop offset="95%" stopColor="#4F46E5" stopOpacity={0} />
                            </linearGradient>
                          </defs>
                          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" />
                          <XAxis
                            dataKey="date"
                            tickLine={false}
                            axisLine={false}
                            tick={{ fontSize: 11, fill: '#64748B' }}
                          />
                          <YAxis
                            tickLine={false}
                            axisLine={false}
                            tick={{ fontSize: 11, fill: '#64748B' }}
                            tickFormatter={(v) => `${currencySymbol}${v}`}
                          />
                          <RechartsTooltip
                            formatter={(v) => [`${currencySymbol}${Number(v).toFixed(2)}`, 'Spent']}
                          />
                          <Area
                            type="monotone"
                            dataKey="amount"
                            stroke="#4F46E5"
                            strokeWidth={3}
                            fillOpacity={1}
                            fill="url(#spendGrad)"
                          />
                        </AreaChart>
                      </ResponsiveContainer>
                    </div>
                  )}
                </div>
              </div>

              {/* End of Month Forecast AI Card */}
              {forecast && (
                <div
                  className="card p-6"
                  style={{
                    background: 'linear-gradient(135deg, #1E1B4B 0%, #312E81 100%)',
                    color: '#FFFFFF',
                    border: 'none',
                    boxShadow: '0 10px 25px -5px rgba(49, 46, 129, 0.4)',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <Sparkles size={20} style={{ color: '#FCD34D' }} />
                      <h3 style={{ fontFamily: 'var(--font-heading)', fontSize: '1.25rem', fontWeight: 700 }}>
                        AI End-of-Month Predictive Forecast
                      </h3>
                    </div>
                    <span
                      className={`badge ${forecast.health_status === 'Healthy' ? 'badge-success' : 'badge-danger'}`}
                      style={{ fontSize: '0.75rem' }}
                    >
                      Status: {forecast.health_status}
                    </span>
                  </div>

                  <p style={{ color: '#E0E7FF', fontSize: '0.9rem', marginBottom: '1.5rem', maxWidth: '700px' }}>
                    Based on your average burn of <strong>{currencySymbol}{forecast.daily_burn_rate.toFixed(2)}/day</strong> over {forecast.days_elapsed} days elapsed ({forecast.days_remaining} days left):
                  </p>

                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', marginBottom: '1rem' }}>
                    <div style={{ backgroundColor: 'rgba(255, 255, 255, 0.1)', padding: '1rem', borderRadius: 'var(--radius-md)' }}>
                      <div style={{ fontSize: '0.75rem', color: '#A5B4FC' }}>Projected Month-End Spend</div>
                      <div style={{ fontSize: '1.5rem', fontWeight: 700 }}>{currencySymbol}{forecast.projected_month_end_spent.toFixed(2)}</div>
                    </div>

                    <div style={{ backgroundColor: 'rgba(255, 255, 255, 0.1)', padding: '1rem', borderRadius: 'var(--radius-md)' }}>
                      <div style={{ fontSize: '0.75rem', color: '#A5B4FC' }}>Projected Balance</div>
                      <div style={{ fontSize: '1.5rem', fontWeight: 700, color: forecast.projected_month_end_balance >= 0 ? '#34D399' : '#F87171' }}>
                        {currencySymbol}{forecast.projected_month_end_balance.toFixed(2)}
                      </div>
                    </div>

                    <div style={{ backgroundColor: 'rgba(255, 255, 255, 0.1)', padding: '1rem', borderRadius: 'var(--radius-md)' }}>
                      <div style={{ fontSize: '0.75rem', color: '#A5B4FC' }}>Budget Status</div>
                      <div style={{ fontSize: '1.25rem', fontWeight: 700, color: forecast.will_exceed_allowance ? '#F87171' : '#34D399' }}>
                        {forecast.will_exceed_allowance ? '⚠️ Exceeding Allowance' : '✅ Within Budget'}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Categorical Distribution Bar Chart */}
              {categoryBreakdown.length > 0 && (
                <div className="card">
                  <div className="card-header">
                    <h3>Expenditure Share by Category</h3>
                  </div>
                  <div className="card-body">
                    <div style={{ width: '100%', height: '240px' }}>
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={categoryBreakdown} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
                          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" />
                          <XAxis dataKey="category" tickLine={false} axisLine={false} tick={{ fontSize: 11, fill: '#64748B' }} />
                          <YAxis tickLine={false} axisLine={false} tick={{ fontSize: 11, fill: '#64748B' }} tickFormatter={(v) => `${currencySymbol}${v}`} />
                          <RechartsTooltip formatter={(v) => [`${currencySymbol}${Number(v).toFixed(2)}`, 'Spent']} />
                          <Bar dataKey="amount" fill="#4F46E5" radius={[6, 6, 0, 0]} />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                </div>
              )}

            </div>
          )}

          {/* ========================================================================= */}
          {/* TAB 6: AI FINANCIAL ADVISOR */}
          {/* ========================================================================= */}
          {activeTab === 'advisor' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
              
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
                <div>
                  <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: '1.25rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <Sparkles size={20} className="text-primary" /> AI Financial Advisor & Habits Engine
                  </h2>
                  <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
                    Continuous analysis powered by Google Gemini heuristics to optimize your student budget.
                  </p>
                </div>

                <div style={{ display: 'flex', gap: '0.75rem' }}>
                  <button
                    type="button"
                    className="btn btn-outline btn-sm"
                    onClick={handleMarkAllRecsRead}
                    disabled={recommendations.every(r => r.is_read)}
                  >
                    <CheckCircle2 size={14} /> Mark All As Read
                  </button>
                  <button
                    type="button"
                    className="btn btn-ai btn-sm"
                    onClick={handleGenerateAI}
                    disabled={aiGenerating}
                  >
                    {aiGenerating ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
                    <span>{aiGenerating ? 'Analyzing Spending...' : 'Re-Run AI Analysis'}</span>
                  </button>
                </div>
              </div>

              {/* Impact Filter Chips */}
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                {['ALL', 'HIGH', 'MEDIUM', 'LOW'].map((lvl) => (
                  <button
                    key={lvl}
                    type="button"
                    className={`btn btn-sm ${recFilterImpact === lvl ? 'btn-primary' : 'btn-outline'}`}
                    onClick={() => setRecFilterImpact(lvl)}
                  >
                    {lvl === 'ALL' ? 'All Insights' : `${lvl.charAt(0) + lvl.slice(1).toLowerCase()} Impact`}
                  </button>
                ))}
              </div>

              {/* Recommendations Feed */}
              {filteredRecs.length === 0 ? (
                <div className="empty-state">
                  <div className="empty-icon-circle">
                    <Sparkles size={28} />
                  </div>
                  <h4>No insights for this filter</h4>
                  <p>Click below to re-run financial habits analysis.</p>
                  <button
                    type="button"
                    className="btn btn-ai"
                    onClick={handleGenerateAI}
                    disabled={aiGenerating}
                  >
                    {aiGenerating ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />}
                    <span>Run AI Analysis</span>
                  </button>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                  {filteredRecs.map((rec) => {
                    const isHigh = rec.impact_level?.toLowerCase() === 'high';
                    const isLow = rec.impact_level?.toLowerCase() === 'low';

                    return (
                      <div
                        key={rec.id}
                        className="card p-5"
                        style={{
                          borderLeft: `5px solid ${isHigh ? 'var(--danger)' : isLow ? 'var(--success)' : 'var(--warning)'}`,
                          opacity: rec.is_read ? 0.8 : 1,
                          transition: 'all 0.2s ease',
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.5rem' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
                            <span style={{ fontSize: '1.25rem' }}>
                              {isHigh ? '🚨' : isLow ? '💡' : '⚡'}
                            </span>
                            <h3 style={{ fontSize: '1.0625rem', fontWeight: 700, color: 'var(--text-main)' }}>
                              {rec.title}
                            </h3>
                          </div>

                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <span
                              className={`badge ${isHigh ? 'badge-danger' : isLow ? 'badge-success' : 'badge-warning'}`}
                            >
                              {rec.impact_level} Impact
                            </span>
                            <span className="badge badge-subtle">
                              {rec.category}
                            </span>
                          </div>
                        </div>

                        <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: '1rem' }}>
                          {rec.message}
                        </p>

                        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', borderTop: '1px solid var(--border-light)', paddingTop: '0.75rem' }}>
                          {!rec.is_read && (
                            <button
                              type="button"
                              className="btn btn-outline btn-sm"
                              onClick={() => handleMarkRecRead(rec.id)}
                            >
                              <CheckCircle2 size={14} /> Mark as Read
                            </button>
                          )}
                          <button
                            type="button"
                            className="btn btn-outline btn-sm"
                            style={{ color: 'var(--danger)' }}
                            onClick={() => handleDeleteRec(rec.id)}
                          >
                            <Trash2 size={14} /> Dismiss
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}

            </div>
          )}

        </main>
      </div>

      {/* ========================================================================= */}
      {/* MODAL: ADD EXPENSE */}
      {/* ========================================================================= */}
      {isExpenseModalOpen && (
        <div className="modal-overlay" onClick={() => setExpenseModalOpen(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Log New Expense</h3>
              <button
                type="button"
                className="btn btn-outline btn-icon"
                onClick={() => setExpenseModalOpen(false)}
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleAddExpense}>
              <div className="modal-body">
                <div className="form-group">
                  <label className="form-label">Title / Item Description *</label>
                  <input
                    type="text"
                    required
                    value={expenseForm.title}
                    onChange={(e) => setExpenseForm({ ...expenseForm, title: e.target.value })}
                    placeholder="e.g. Chipotle Bowl, Calculus Textbook"
                    className="input-field"
                  />
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                  <div className="form-group">
                    <label className="form-label">Amount ({currencySymbol}) *</label>
                    <input
                      type="number"
                      step="0.01"
                      min="0.01"
                      required
                      value={expenseForm.amount}
                      onChange={(e) => setExpenseForm({ ...expenseForm, amount: e.target.value })}
                      placeholder="14.50"
                      className="input-field"
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Category *</label>
                    <select
                      className="input-field"
                      value={expenseForm.category}
                      onChange={(e) => setExpenseForm({ ...expenseForm, category: e.target.value })}
                    >
                      <option value="Food">Food & Dining</option>
                      <option value="Books">Books & Academics</option>
                      <option value="Transport">Transportation</option>
                      <option value="Entertainment">Entertainment</option>
                      <option value="Fitness">Fitness & Health</option>
                      <option value="Utilities">Utilities & Rent</option>
                      <option value="Shopping">Shopping</option>
                      <option value="Other">Other</option>
                    </select>
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                  <div className="form-group">
                    <label className="form-label">Payment Method</label>
                    <select
                      className="input-field"
                      value={expenseForm.payment_method}
                      onChange={(e) => setExpenseForm({ ...expenseForm, payment_method: e.target.value })}
                    >
                      <option value="UPI">UPI</option>
                      <option value="Debit Card">Debit Card</option>
                      <option value="Credit Card">Credit Card</option>
                      <option value="Cash">Cash</option>
                      <option value="Online">Online Banking</option>
                    </select>
                  </div>

                  <div className="form-group">
                    <label className="form-label">Date *</label>
                    <input
                      type="date"
                      required
                      value={expenseForm.date}
                      onChange={(e) => setExpenseForm({ ...expenseForm, date: e.target.value })}
                      className="input-field"
                    />
                  </div>
                </div>

                <div className="form-group">
                  <label className="form-label">Notes (Optional)</label>
                  <input
                    type="text"
                    value={expenseForm.notes}
                    onChange={(e) => setExpenseForm({ ...expenseForm, notes: e.target.value })}
                    placeholder="e.g. Split with roomate"
                    className="input-field"
                  />
                </div>
              </div>

              <div className="modal-footer">
                <button type="button" className="btn btn-outline" onClick={() => setExpenseModalOpen(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  Save Expense
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODAL: SET BUDGET */}
      {/* ========================================================================= */}
      {isBudgetModalOpen && (
        <div className="modal-overlay" onClick={() => setBudgetModalOpen(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Set Category Budget</h3>
              <button
                type="button"
                className="btn btn-outline btn-icon"
                onClick={() => setBudgetModalOpen(false)}
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleSetBudget}>
              <div className="modal-body">
                <div className="form-group">
                  <label className="form-label">Category</label>
                  <select
                    className="input-field"
                    value={budgetForm.category}
                    onChange={(e) => setBudgetForm({ ...budgetForm, category: e.target.value })}
                  >
                    <option value="Food">Food & Dining</option>
                    <option value="Books">Books & Academics</option>
                    <option value="Transport">Transportation</option>
                    <option value="Entertainment">Entertainment</option>
                    <option value="Fitness">Fitness & Health</option>
                    <option value="Utilities">Utilities & Rent</option>
                    <option value="Shopping">Shopping</option>
                    <option value="Other">Other</option>
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label">Monthly Limit ({currencySymbol}) *</label>
                  <input
                    type="number"
                    step="1"
                    min="1"
                    required
                    value={budgetForm.monthly_limit}
                    onChange={(e) => setBudgetForm({ ...budgetForm, monthly_limit: e.target.value })}
                    placeholder="e.g. 200.00"
                    className="input-field"
                  />
                </div>
              </div>

              <div className="modal-footer">
                <button type="button" className="btn btn-outline" onClick={() => setBudgetModalOpen(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  Set Budget
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODAL: CREATE SAVINGS GOAL */}
      {/* ========================================================================= */}
      {isGoalModalOpen && (
        <div className="modal-overlay" onClick={() => setGoalModalOpen(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Create Savings Target</h3>
              <button
                type="button"
                className="btn btn-outline btn-icon"
                onClick={() => setGoalModalOpen(false)}
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleCreateGoal}>
              <div className="modal-body">
                <div className="form-group">
                  <label className="form-label">Goal Title *</label>
                  <input
                    type="text"
                    required
                    value={goalForm.title}
                    onChange={(e) => setGoalForm({ ...goalForm, title: e.target.value })}
                    placeholder="e.g. MacBook Pro M4 Fund, Summer Roadtrip"
                    className="input-field"
                  />
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                  <div className="form-group">
                    <label className="form-label">Target Amount ({currencySymbol}) *</label>
                    <input
                      type="number"
                      step="1"
                      min="1"
                      required
                      value={goalForm.target_amount}
                      onChange={(e) => setGoalForm({ ...goalForm, target_amount: e.target.value })}
                      placeholder="1000.00"
                      className="input-field"
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Already Saved ({currencySymbol})</label>
                    <input
                      type="number"
                      step="1"
                      min="0"
                      value={goalForm.current_amount}
                      onChange={(e) => setGoalForm({ ...goalForm, current_amount: e.target.value })}
                      placeholder="100.00"
                      className="input-field"
                    />
                  </div>
                </div>

                <div className="form-group">
                  <label className="form-label">Target Deadline *</label>
                  <input
                    type="date"
                    required
                    value={goalForm.deadline}
                    onChange={(e) => setGoalForm({ ...goalForm, deadline: e.target.value })}
                    className="input-field"
                  />
                </div>
              </div>

              <div className="modal-footer">
                <button type="button" className="btn btn-outline" onClick={() => setGoalModalOpen(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  Create Goal
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODAL: DEPOSIT TO GOAL */}
      {/* ========================================================================= */}
      {isDepositModalOpen && selectedGoalForDeposit && (
        <div className="modal-overlay" onClick={() => setDepositModalOpen(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Deposit into '{selectedGoalForDeposit.title}'</h3>
              <button
                type="button"
                className="btn btn-outline btn-icon"
                onClick={() => setDepositModalOpen(false)}
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleDepositToGoal}>
              <div className="modal-body">
                <div style={{ backgroundColor: 'var(--primary-light)', padding: '1rem', borderRadius: 'var(--radius-md)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Current Progress</div>
                    <div style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--primary)' }}>
                      {currencySymbol}{selectedGoalForDeposit.current_amount.toFixed(2)} / {currencySymbol}{selectedGoalForDeposit.target_amount.toFixed(2)}
                    </div>
                  </div>
                  <span className="badge badge-primary">
                    {Math.round((selectedGoalForDeposit.current_amount / selectedGoalForDeposit.target_amount) * 100)}%
                  </span>
                </div>

                <div className="form-group">
                  <label className="form-label">Deposit Amount ({currencySymbol}) *</label>
                  <input
                    type="number"
                    step="0.01"
                    min="1"
                    required
                    value={depositAmount}
                    onChange={(e) => setDepositAmount(e.target.value)}
                    placeholder="50.00"
                    className="input-field"
                    autoFocus
                  />
                </div>

                {/* Quick Chips */}
                <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                  {[10, 25, 50, 100].map((amt) => (
                    <button
                      key={amt}
                      type="button"
                      className="btn btn-outline btn-sm"
                      onClick={() => setDepositAmount(amt.toString())}
                    >
                      +{currencySymbol}{amt}
                    </button>
                  ))}
                </div>
              </div>

              <div className="modal-footer">
                <button type="button" className="btn btn-outline" onClick={() => setDepositModalOpen(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  Confirm Deposit
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
};

export default Dashboard;
