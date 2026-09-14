/**
 * AuthContext — global authentication state for the entire app.
 * Provides: current user, loading state, login/logout/refresh helpers.
 */
import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import {
  AuthUser,
  apiGetMe,
  apiLogin,
  apiLogout as serviceLogout,
  clearToken,
  getToken,
  getStoredUser,
} from '../services/authService';

interface AuthContextValue {
  user: AuthUser | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  loginWithGoogle: (idToken: string) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
  setUser: React.Dispatch<React.SetStateAction<AuthUser | null>>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(getStoredUser);
  const [isLoading, setIsLoading] = useState<boolean>(!!getToken());

  // On mount, if a token exists, validate it with the backend
  useEffect(() => {
    const token = getToken();
    if (!token) { setIsLoading(false); return; }
    apiGetMe()
      .then(setUser)
      .catch(() => { clearToken(); setUser(null); })
      .finally(() => setIsLoading(false));
  }, []);

  // Listen for global 401 events dispatched by authFetch
  useEffect(() => {
    const handle = () => { clearToken(); setUser(null); };
    window.addEventListener('auth:expired', handle);
    return () => window.removeEventListener('auth:expired', handle);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const u = await apiLogin(email, password);
    setUser(u);
  }, []);

  const loginWithGoogle = useCallback(async (idToken: string) => {
    const { apiGoogleLogin } = await import('../services/authService');
    const u = await apiGoogleLogin(idToken);
    setUser(u);
  }, []);

  const logout = useCallback(() => {
    serviceLogout();
    setUser(null);
  }, []);

  const refreshUser = useCallback(async () => {
    try { const u = await apiGetMe(); setUser(u); } catch { /* silent */ }
  }, []);

  return (
    <AuthContext.Provider
      value={{ user, isLoading, isAuthenticated: !!user, login, loginWithGoogle, logout, refreshUser, setUser }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
}
