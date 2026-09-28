import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../auth';
import { Sparkles, UserPlus, LogIn, ArrowRight, Loader2, Mail, ShieldCheck, Lock } from 'lucide-react';

const Onboarding = () => {
  const navigate = useNavigate();
  const { student, authReady, login, register } = useAuth();
  const [activeTab, setActiveTab] = useState('login'); // 'login' | 'register'
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  // Already authenticated -> skip onboarding.
  useEffect(() => {
    if (authReady && student) navigate('/dashboard', { replace: true });
  }, [authReady, student, navigate]);

  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: '',
    monthly_allowance: '',
    currency: 'USD',
    college_year: 'Sophomore',
  });

  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setLoading(true);
    setErrorMsg('');

    try {
      if (!formData.password || formData.password.length < 6) {
        setErrorMsg('Password must be at least 6 characters.');
        setLoading(false);
        return;
      }
      await register({
        name: formData.name.trim(),
        email: formData.email.trim().toLowerCase(),
        password: formData.password,
        monthly_allowance: parseFloat(formData.monthly_allowance) || 0,
        currency: formData.currency,
        college_year: formData.college_year,
      });
      navigate('/dashboard');
    } catch (err) {
      setErrorMsg(err.message || 'Registration failed.');
    } finally {
      setLoading(false);
    }
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    if (!loginEmail.trim() || !loginPassword) {
      setErrorMsg('Please enter both email and password.');
      return;
    }
    setLoading(true);
    setErrorMsg('');
    try {
      await login(loginEmail.trim(), loginPassword);
      navigate('/dashboard');
    } catch (err) {
      setErrorMsg(err.message || 'Incorrect email or password.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', padding: '2rem 1rem', background: 'linear-gradient(135deg, #0F172A 0%, #1E1B4B 50%, #0F172A 100%)' }}>
      
      {/* Brand Header */}
      <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
        <div style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: '56px', height: '56px', borderRadius: '16px', background: 'linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%)', boxShadow: '0 8px 24px rgba(79, 70, 229, 0.5)', fontSize: '1.75rem', marginBottom: '0.75rem' }}>
          💎
        </div>
        <h1 style={{ fontFamily: 'var(--font-heading)', color: '#FFFFFF', fontSize: '1.875rem', fontWeight: 800, letterSpacing: '-0.03em', marginBottom: '0.25rem' }}>
          SmartFinance AI
        </h1>
        <p style={{ color: '#94A3B8', fontSize: '0.9375rem', maxWidth: '380px', margin: '0 auto' }}>
          Your private, student-centric AI personal finance tracker & budget optimizer.
        </p>
      </div>

      {/* Main Authentication Card */}
      <div className="card auth-card" style={{ width: '100%', borderRadius: 'var(--radius-xl)', boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.45)', border: '1px solid rgba(255, 255, 255, 0.1)' }}>

        {/* Tab Toggle: Sign In vs Create Account */}
        <div className="segmented-tabs" style={{ marginBottom: '1.5rem' }}>
          <button 
            type="button" 
            className={`segmented-tab ${activeTab === 'login' ? 'active' : ''}`}
            onClick={() => { setActiveTab('login'); setErrorMsg(''); }}
          >
            <LogIn size={15} style={{ display: 'inline', marginRight: '5px', verticalAlign: '-2px' }} />
            Sign In
          </button>
          <button 
            type="button" 
            className={`segmented-tab ${activeTab === 'register' ? 'active' : ''}`}
            onClick={() => { setActiveTab('register'); setErrorMsg(''); }}
          >
            <UserPlus size={15} style={{ display: 'inline', marginRight: '5px', verticalAlign: '-2px' }} />
            Create Account
          </button>
        </div>

        {errorMsg && (
          <div style={{ padding: '0.75rem 1rem', marginBottom: '1.25rem', backgroundColor: 'var(--danger-light)', border: '1px solid var(--danger-border)', borderRadius: 'var(--radius-md)', color: 'var(--danger-text)', fontSize: '0.8125rem' }}>
            {errorMsg}
          </div>
        )}

        {/* TAB 1: SIGN IN */}
        {activeTab === 'login' && (
          <form onSubmit={handleLogin} className="flex-col gap-4">
            <div className="form-group">
              <label className="form-label">Email Address</label>
              <div style={{ position: 'relative' }}>
                <input
                  type="email"
                  value={loginEmail}
                  onChange={(e) => setLoginEmail(e.target.value)}
                  placeholder="Enter your email (e.g. sourab@gmail.com)"
                  required
                  autoFocus
                  className="input-field"
                  style={{ paddingLeft: '2.4rem' }}
                />
                <Mail size={16} style={{ position: 'absolute', left: '0.85rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
              </div>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                Enter your email and password to securely open your personal finances.
              </p>
            </div>

            <div className="form-group">
              <label className="form-label">Password</label>
              <div style={{ position: 'relative' }}>
                <input
                  type="password"
                  value={loginPassword}
                  onChange={(e) => setLoginPassword(e.target.value)}
                  placeholder="Enter your password"
                  required
                  autoComplete="current-password"
                  className="input-field"
                  style={{ paddingLeft: '2.4rem' }}
                />
                <Lock size={16} style={{ position: 'absolute', left: '0.85rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
              </div>
            </div>

            <button 
              type="submit" 
              className="btn btn-primary w-full"
              style={{ padding: '0.75rem', marginTop: '0.5rem' }}
              disabled={loading}
            >
              {loading ? (
                <>
                  <Loader2 size={16} className="animate-spin" /> Signing In...
                </>
              ) : (
                <>
                  Sign In to My Account <ArrowRight size={16} />
                </>
              )}
            </button>

            <div style={{ textAlign: 'center', marginTop: '0.5rem' }}>
              <button
                type="button"
                onClick={() => { setActiveTab('register'); setErrorMsg(''); }}
                style={{ background: 'none', border: 'none', color: 'var(--primary)', fontSize: '0.8125rem', cursor: 'pointer', fontWeight: 600 }}
              >
                Don't have an account? Create one here
              </button>
            </div>
          </form>
        )}

        {/* TAB 2: CREATE ACCOUNT */}
        {activeTab === 'register' && (
          <form onSubmit={handleRegister} className="flex-col gap-4">
            <div className="form-group">
              <label className="form-label">Full Name</label>
              <input 
                type="text" 
                name="name" 
                required
                value={formData.name}
                onChange={handleChange}
                placeholder="e.g. Alex Johnson" 
                className="input-field"
              />
            </div>
            
            <div className="form-group">
              <label className="form-label">Email Address</label>
              <input
                type="email"
                name="email"
                required
                value={formData.email}
                onChange={handleChange}
                placeholder="alex@university.edu"
                className="input-field"
              />
            </div>

            <div className="form-group">
              <label className="form-label">Password (min 6 characters)</label>
              <input
                type="password"
                name="password"
                required
                minLength={6}
                value={formData.password}
                onChange={handleChange}
                placeholder="Choose a secure password"
                autoComplete="new-password"
                className="input-field"
              />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
              <div className="form-group">
                <label className="form-label">Monthly Allowance</label>
                <input 
                  type="number" 
                  name="monthly_allowance" 
                  required
                  min="0"
                  step="0.01"
                  value={formData.monthly_allowance}
                  onChange={handleChange}
                  placeholder="800.00" 
                  className="input-field"
                />
              </div>

              <div className="form-group">
                <label className="form-label">Currency</label>
                <select 
                  name="currency" 
                  value={formData.currency} 
                  onChange={handleChange} 
                  className="input-field"
                >
                  <option value="USD">USD ($)</option>
                  <option value="EUR">EUR (€)</option>
                  <option value="GBP">GBP (£)</option>
                  <option value="INR">INR (₹)</option>
                  <option value="CAD">CAD ($)</option>
                </select>
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">College Year / Academic Status</label>
              <select 
                name="college_year" 
                value={formData.college_year} 
                onChange={handleChange} 
                className="input-field"
              >
                <option value="Freshman">Freshman (1st Year)</option>
                <option value="Sophomore">Sophomore (2nd Year)</option>
                <option value="Junior">Junior (3rd Year)</option>
                <option value="Senior">Senior (4th Year)</option>
                <option value="Graduate">Graduate Student</option>
              </select>
            </div>

            <button 
              type="submit"
              className="btn btn-primary w-full" 
              style={{ marginTop: '0.5rem', padding: '0.75rem' }}
              disabled={loading}
            >
              {loading ? (
                <>
                  <Loader2 size={16} className="animate-spin" /> Creating Profile...
                </>
              ) : (
                <>
                  Create Private Account <ArrowRight size={16} />
                </>
              )}
            </button>

            <div style={{ textAlign: 'center', marginTop: '0.5rem' }}>
              <button
                type="button"
                onClick={() => { setActiveTab('login'); setErrorMsg(''); }}
                style={{ background: 'none', border: 'none', color: 'var(--primary)', fontSize: '0.8125rem', cursor: 'pointer', fontWeight: 600 }}
              >
                Already have an account? Sign in here
              </button>
            </div>
          </form>
        )}

      </div>

      <div style={{ marginTop: '2rem', color: '#64748B', fontSize: '0.8125rem', textAlign: 'center', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
        <ShieldCheck size={16} /> Strict Account Privacy: Only you can view your personal finance records.
      </div>

    </div>
  );
};

export default Onboarding;
