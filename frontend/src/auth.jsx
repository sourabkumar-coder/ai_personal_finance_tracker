import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { api, getToken, setToken, clearAuthStorage } from './api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setTokenState] = useState(() => getToken());
  const [student, setStudent] = useState(null);
  const [authReady, setAuthReady] = useState(false);

  const rememberStudent = (s) => {
    setStudent(s);
    try {
      if (s && s.id) localStorage.setItem('student_id', String(s.id));
    } catch {
      // storage unavailable — session still works in memory
    }
  };

  // On boot: validate any persisted token against /auth/me.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (!getToken()) {
        setAuthReady(true);
        return;
      }
      try {
        const me = await api.getMe();
        if (!cancelled) rememberStudent(me);
      } catch {
        if (!cancelled) {
          clearAuthStorage();
          setTokenState(null);
          setStudent(null);
        }
      } finally {
        if (!cancelled) setAuthReady(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (email, password) => {
    const data = await api.authLogin(email, password);
    setToken(data.access_token);
    setTokenState(data.access_token);
    const me = await api.getMe();
    rememberStudent(me);
    return me;
  }, []);

  const register = useCallback(async (fields) => {
    const data = await api.authRegister(fields);
    setToken(data.access_token);
    setTokenState(data.access_token);
    rememberStudent(data.student);
    return data.student;
  }, []);

  const logout = useCallback(() => {
    clearAuthStorage();
    setTokenState(null);
    setStudent(null);
  }, []);

  return (
    <AuthContext.Provider value={{ token, student, authReady, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
