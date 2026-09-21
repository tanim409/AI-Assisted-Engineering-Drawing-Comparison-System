/**
 * AuthPage — Login & Registration screen.
 * Tab-switches between Login and Register forms.
 */
import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { apiRegister } from '../services/authService';
import { Mail, CheckCircle2, AlertCircle, RefreshCw, Loader2, ArrowRight } from 'lucide-react';

interface AuthPageProps {
  /** Called after successful login so App can switch views */
  onAuthenticated: () => void;
  /** Pre-select which tab to show */
  initialTab?: 'login' | 'register';
  /** Optional close handler when rendered as modal */
  onClose?: () => void;
}

export const AuthPage: React.FC<AuthPageProps> = ({ onAuthenticated, initialTab = 'login', onClose }) => {
  const { login, register, loginWithGoogle } = useAuth();
  const [tab, setTab] = useState<'login' | 'register'>(initialTab);
  const [googleLoading, setGoogleLoading] = useState(false);

  const handleGoogleLogin = async (idToken: string) => {
    setLoginError('');
    setGoogleLoading(true);
    try {
      await loginWithGoogle(idToken);
      onAuthenticated();
    } catch (err: any) {
      setLoginError(err.message || 'Google sign-in failed');
    } finally {
      setGoogleLoading(false);
    }
  };

  const triggerGooglePrompt = () => {
    const googleClientId = ((import.meta as any).env?.VITE_GOOGLE_CLIENT_ID as string) || '';
    setLoginError('');

    if (!(window as any).google?.accounts) {
      setLoginError('Google Sign-In SDK is loading. Please try again in a moment.');
      return;
    }

    try {
      // 1. First try OAuth2 token client popup flow if available
      if ((window as any).google.accounts.oauth2) {
        const client = (window as any).google.accounts.oauth2.initTokenClient({
          client_id: googleClientId,
          scope: 'email profile openid',
          callback: async (tokenResponse: any) => {
            if (tokenResponse.access_token) {
              handleGoogleLogin(tokenResponse.id_token || tokenResponse.access_token);
            } else if (tokenResponse.error) {
              setLoginError(`Google OAuth error: ${tokenResponse.error}`);
            }
          },
        });
        client.requestAccessToken();
        return;
      }

      // 2. Fallback to GIS ID Token prompt flow
      if ((window as any).google.accounts.id) {
        (window as any).google.accounts.id.initialize({
          client_id: googleClientId,
          callback: (response: any) => {
            if (response.credential) {
              handleGoogleLogin(response.credential);
            } else {
              setLoginError('Google Sign-In was cancelled or failed.');
            }
          },
        });
        (window as any).google.accounts.id.prompt((notification: any) => {
          if (notification.isNotDisplayed() || notification.isSkippedMoment()) {
            (window as any).google.accounts.id.renderButton(
              document.getElementById('google-btn-container'),
              { theme: 'outline', size: 'large', width: '100%' }
            );
          }
        });
      }
    } catch (e: any) {
      setLoginError(e.message || 'Could not launch Google Sign-In.');
    }
  };

  // ── Login state ──────────────────────────────────────────────────────────
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [loginError, setLoginError] = useState('');
  const [loginLoading, setLoginLoading] = useState(false);
  const [showLoginPass, setShowLoginPass] = useState(false);

  // ── Register state ───────────────────────────────────────────────────────
  const [regEmail, setRegEmail] = useState('');
  const [regPassword, setRegPassword] = useState('');
  const [regConfirm, setRegConfirm] = useState('');
  const [regError, setRegError] = useState('');
  const [regLoading, setRegLoading] = useState(false);
  const [showRegPass, setShowRegPass] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoginError('');
    setLoginLoading(true);
    try {
      await login(loginEmail, loginPassword);
      onAuthenticated();
    } catch (err: any) {
      setLoginError(err.message || 'Login failed');
    } finally {
      setLoginLoading(false);
    }
  };

  const EMAIL_DOMAIN_REGEX = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setRegError('');

    if (!EMAIL_DOMAIN_REGEX.test(regEmail.trim())) {
      setRegError('Please enter a valid email address with a complete domain (e.g. user@gmail.com).');
      return;
    }
    if (regPassword !== regConfirm) {
      setRegError('Passwords do not match');
      return;
    }
    if (regPassword.length < 6) {
      setRegError('Password must be at least 6 characters');
      return;
    }
    setRegLoading(true);
    try {
      await register(regEmail, regPassword);
      onAuthenticated();
    } catch (err: any) {
      setRegError(err.message || 'Registration failed');
    } finally {
      setRegLoading(false);
    }
  };

  const isModal = !!onClose;



  // Card content — shared between standalone and modal renders
  const card = (
    <div className="relative w-full max-w-md">
        {/* Brand */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-white/5 border border-white/10 mb-4 backdrop-blur-sm">
            <span className="text-white text-2xl font-bold">Δ</span>
          </div>
          <h1 className="text-white text-2xl font-bold tracking-tight">Engineering Drawing Diff</h1>
          <p className="text-white/40 text-sm mt-1">CAD Comparison & Review Platform</p>
        </div>

        {/* Card */}
        <div className="bg-white/5 border border-white/10 rounded-2xl backdrop-blur-md p-8 shadow-2xl">
          {/* Tabs */}
          <div className="flex gap-1 bg-white/5 rounded-xl p-1 mb-7">
            {(['login', 'register'] as const).map((t) => (
              <button
                key={t}
                id={`auth-tab-${t}`}
                onClick={() => {
                  setTab(t);
                  setLoginError('');
                  setRegError('');
                }}
                className={`flex-1 py-2 text-sm font-medium rounded-lg transition-all duration-200 cursor-pointer
                  ${tab === t
                    ? 'bg-white text-[#0A0A0A] shadow-sm'
                    : 'text-white/50 hover:text-white/80'
                  }`}
              >
                {t === 'login' ? 'Sign In' : 'Create Account'}
              </button>
            ))}
          </div>

          {/* ── Login Form ── */}
          {tab === 'login' && (
            <div className="space-y-4">
              <button
                type="button"
                id="btn-google-login"
                onClick={triggerGooglePrompt}
                disabled={googleLoading}
                className="w-full flex items-center justify-center gap-3 bg-white/10 hover:bg-white/15 border border-white/15 text-white font-medium py-3 rounded-xl text-sm transition-all duration-200 cursor-pointer disabled:opacity-50"
              >
                <svg className="w-4 h-4 shrink-0" viewBox="0 0 24 24">
                  <path
                    fill="#EA4335"
                    d="M12 5c1.6 0 3 .6 4.1 1.6l3.1-3.1C17.3 1.7 14.8 1 12 1 7.5 1 3.7 3.6 1.9 7.3l3.7 2.9C6.5 7.4 9 5 12 5z"
                  />
                  <path
                    fill="#4285F4"
                    d="M23.5 12.3c0-.8-.1-1.6-.2-2.3H12v4.5h6.5c-.3 1.5-1.1 2.8-2.4 3.7l3.7 2.9c2.2-2 3.7-5 3.7-8.8z"
                  />
                  <path
                    fill="#FBBC05"
                    d="M5.6 14.8c-.2-.7-.4-1.5-.4-2.3s.2-1.6.4-2.3L1.9 7.3C.7 9.7 0 12 0 14.5s.7 4.8 1.9 7.2l3.7-2.9z"
                  />
                  <path
                    fill="#34A853"
                    d="M12 23c3.2 0 6-1.1 8-3l-3.7-2.9c-1.1.7-2.5 1.2-4.3 1.2-3 0-5.5-2.4-6.4-5.2L1.9 16C3.7 19.7 7.5 23 12 23z"
                  />
                </svg>
                <span>{googleLoading ? 'Connecting to Google…' : 'Continue with Google'}</span>
              </button>

              <div className="flex items-center gap-3 my-2">
                <div className="flex-1 h-px bg-white/10" />
                <span className="text-white/30 text-xs uppercase font-mono">or</span>
                <div className="flex-1 h-px bg-white/10" />
              </div>

              <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <label className="block text-white/60 text-xs font-medium mb-1.5" htmlFor="login-email">
                  Email address
                </label>
                <input
                  id="login-email"
                  type="email"
                  required
                  autoComplete="email"
                  value={loginEmail}
                  onChange={(e) => setLoginEmail(e.target.value)}
                  placeholder="engineer@company.com"
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white text-sm placeholder-white/20
                    focus:outline-none focus:border-white/30 focus:bg-white/8 transition-all"
                />
              </div>
              <div>
                <label className="block text-white/60 text-xs font-medium mb-1.5" htmlFor="login-password">
                  Password
                </label>
                <div className="relative">
                  <input
                    id="login-password"
                    type={showLoginPass ? 'text' : 'password'}
                    required
                    autoComplete="current-password"
                    value={loginPassword}
                    onChange={(e) => setLoginPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 pr-11 text-white text-sm placeholder-white/20
                      focus:outline-none focus:border-white/30 focus:bg-white/8 transition-all"
                  />
                  <button
                    type="button"
                    tabIndex={-1}
                    onClick={() => setShowLoginPass((p) => !p)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-white/30 hover:text-white/60 transition-colors"
                    aria-label="Toggle password visibility"
                  >
                    {showLoginPass ? '🙈' : '👁'}
                  </button>
                </div>
              </div>

              {loginError && (
                <div className="bg-red-500/10 border border-red-500/30 text-red-400 text-sm rounded-xl p-4 flex items-start gap-2.5">
                  <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                  <span className="flex-1">{loginError}</span>
                </div>
              )}

              <button
                id="btn-login-submit"
                type="submit"
                disabled={loginLoading}
                className="w-full bg-white text-[#0A0A0A] font-semibold py-3 rounded-xl text-sm
                  hover:bg-white/90 disabled:opacity-50 disabled:cursor-not-allowed
                  transition-all duration-200 active:scale-[0.98]"
              >
                {loginLoading ? 'Signing in…' : 'Sign In'}
              </button>
            </form>
          </div>
        )}

          {/* ── Register Form ── */}
          {tab === 'register' && (
            <form onSubmit={handleRegister} className="space-y-4">
              <div>
                <label className="block text-white/60 text-xs font-medium mb-1.5" htmlFor="reg-email">
                  Work email address
                </label>
                <input
                  id="reg-email"
                  type="email"
                  required
                  autoComplete="email"
                  value={regEmail}
                  onChange={(e) => setRegEmail(e.target.value)}
                  placeholder="engineer@company.com"
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white text-sm placeholder-white/20
                    focus:outline-none focus:border-white/30 transition-all"
                />
              </div>
              <div>
                <label className="block text-white/60 text-xs font-medium mb-1.5" htmlFor="reg-password">
                  Password <span className="text-white/30">(min 6 chars)</span>
                </label>
                <div className="relative">
                  <input
                    id="reg-password"
                    type={showRegPass ? 'text' : 'password'}
                    required
                    minLength={6}
                    autoComplete="new-password"
                    value={regPassword}
                    onChange={(e) => setRegPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 pr-11 text-white text-sm placeholder-white/20
                      focus:outline-none focus:border-white/30 transition-all"
                  />
                  <button
                    type="button"
                    tabIndex={-1}
                    onClick={() => setShowRegPass((p) => !p)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-white/30 hover:text-white/60 transition-colors"
                  >
                    {showRegPass ? '🙈' : '👁'}
                  </button>
                </div>
              </div>
              <div>
                <label className="block text-white/60 text-xs font-medium mb-1.5" htmlFor="reg-confirm">
                  Confirm password
                </label>
                <input
                  id="reg-confirm"
                  type="password"
                  required
                  autoComplete="new-password"
                  value={regConfirm}
                  onChange={(e) => setRegConfirm(e.target.value)}
                  placeholder="••••••••"
                  className={`w-full bg-white/5 border rounded-xl px-4 py-3 text-white text-sm placeholder-white/20
                    focus:outline-none transition-all
                    ${regConfirm && regConfirm !== regPassword
                      ? 'border-red-500/50 focus:border-red-500/70'
                      : 'border-white/10 focus:border-white/30'}`}
                />
              </div>

              {/* Strength indicator */}
              {regPassword.length > 0 && (
                <PasswordStrengthBar password={regPassword} />
              )}

              {regError && (
                <div className="bg-red-500/10 border border-red-500/30 text-red-400 text-sm rounded-xl px-4 py-3">
                  {regError}
                </div>
              )}

              <button
                id="btn-register-submit"
                type="submit"
                disabled={regLoading}
                className="w-full bg-white text-[#0A0A0A] font-semibold py-3 rounded-xl text-sm
                  hover:bg-white/90 disabled:opacity-50 disabled:cursor-not-allowed
                  transition-all duration-200 active:scale-[0.98]"
              >
                {regLoading ? 'Creating account…' : 'Create Account'}
              </button>

              <p className="text-white/30 text-xs text-center">
                Create an account to start comparing engineering drawings.
              </p>
            </form>
          )}
        </div>
      </div>
  );

  if (isModal) return card;

  return (
    <div
      id="auth-page"
      className="min-h-screen bg-gradient-to-br from-[#0A0A0A] via-[#111111] to-[#1a1a2e] flex items-center justify-center px-4"
    >
      {/* Ambient glow */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-blue-500/5 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-80 h-80 bg-indigo-500/5 rounded-full blur-3xl" />
      </div>
      {card}
    </div>
  );
};

// ─── Password Strength Bar ────────────────────────────────────────────────────

function PasswordStrengthBar({ password }: { password: string }) {
  const score = getPasswordScore(password);
  const labels = ['Very weak', 'Weak', 'Fair', 'Strong', 'Very strong'];
  const colors = ['bg-red-500', 'bg-orange-500', 'bg-yellow-500', 'bg-emerald-500', 'bg-emerald-400'];
  return (
    <div>
      <div className="flex gap-1 mb-1">
        {[0, 1, 2, 3, 4].map((i) => (
          <div
            key={i}
            className={`h-1 flex-1 rounded-full transition-all duration-300 ${i <= score ? colors[score] : 'bg-white/10'}`}
          />
        ))}
      </div>
      <p className="text-white/30 text-xs">{labels[score]}</p>
    </div>
  );
}

function getPasswordScore(p: string): number {
  let score = 0;
  if (p.length >= 8) score++;
  if (p.length >= 12) score++;
  if (/[A-Z]/.test(p)) score++;
  if (/[0-9]/.test(p)) score++;
  if (/[^A-Za-z0-9]/.test(p)) score++;
  return Math.min(4, score);
}


