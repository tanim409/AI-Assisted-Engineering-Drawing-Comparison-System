/**
 * AuthPage — Login & Registration screen.
 * Tab-switches between Login and Register forms.
 */
import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { apiRegister, apiResendVerification } from '../services/authService';
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
  const { login } = useAuth();
  const [tab, setTab] = useState<'login' | 'register'>(initialTab);

  // ── Login state ──────────────────────────────────────────────────────────
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [loginError, setLoginError] = useState('');
  const [isUnverifiedError, setIsUnverifiedError] = useState(false);
  const [loginLoading, setLoginLoading] = useState(false);
  const [showLoginPass, setShowLoginPass] = useState(false);

  // Resend from login form
  const [loginResendLoading, setLoginResendLoading] = useState(false);
  const [loginResendSuccess, setLoginResendSuccess] = useState(false);

  // ── Register state ───────────────────────────────────────────────────────
  const [regEmail, setRegEmail] = useState('');
  const [regPassword, setRegPassword] = useState('');
  const [regConfirm, setRegConfirm] = useState('');
  const [regError, setRegError] = useState('');
  const [regLoading, setRegLoading] = useState(false);
  const [showRegPass, setShowRegPass] = useState(false);

  // Registered success screen (Check Email screen)
  const [registeredEmail, setRegisteredEmail] = useState<string | null>(null);
  const [checkScreenResendLoading, setCheckScreenResendLoading] = useState(false);
  const [checkScreenResendSuccess, setCheckScreenResendSuccess] = useState(false);

  // ── Forgot Password view ─────────────────────────────────────────────────
  const [showForgot, setShowForgot] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoginError('');
    setIsUnverifiedError(false);
    setLoginResendSuccess(false);
    setLoginLoading(true);
    try {
      await login(loginEmail, loginPassword);
      onAuthenticated();
    } catch (err: any) {
      const msg = err.message || 'Login failed';
      setLoginError(msg);
      if (msg.toLowerCase().includes('verify your email')) {
        setIsUnverifiedError(true);
      }
    } finally {
      setLoginLoading(false);
    }
  };

  const handleLoginResendVerification = async () => {
    if (!loginEmail) return;
    setLoginResendLoading(true);
    setLoginResendSuccess(false);
    try {
      await apiResendVerification(loginEmail);
      setLoginResendSuccess(true);
    } catch (err: any) {
      setLoginError(err?.message || 'Could not send verification email.');
    } finally {
      setLoginResendLoading(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setRegError('');
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
      await apiRegister(regEmail, regPassword);
      setRegisteredEmail(regEmail);
    } catch (err: any) {
      setRegError(err.message || 'Registration failed');
    } finally {
      setRegLoading(false);
    }
  };

  const handleCheckScreenResend = async () => {
    if (!registeredEmail) return;
    setCheckScreenResendLoading(true);
    setCheckScreenResendSuccess(false);
    try {
      await apiResendVerification(registeredEmail);
      setCheckScreenResendSuccess(true);
    } catch {
      // Best effort
    } finally {
      setCheckScreenResendLoading(false);
    }
  };

  const isModal = !!onClose;

  if (showForgot) {
    const forgotPanel = <ForgotPasswordPanel onBack={() => setShowForgot(false)} />;
    if (isModal) return forgotPanel;
    return (
      <div className="min-h-screen bg-gradient-to-br from-[#0A0A0A] via-[#111111] to-[#1a1a2e] flex items-center justify-center px-4">
        {forgotPanel}
      </div>
    );
  }

  // ── "Check Your Email" Post-Registration Screen ──
  if (registeredEmail) {
    const checkEmailCard = (
      <div className="relative w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-white/5 border border-white/10 mb-4 backdrop-blur-sm">
            <span className="text-white text-2xl font-bold">Δ</span>
          </div>
          <h1 className="text-white text-2xl font-bold tracking-tight">Engineering Review</h1>
        </div>

        <div className="bg-white/5 border border-white/10 rounded-2xl backdrop-blur-md p-8 shadow-2xl space-y-6 text-center">
          <div className="w-14 h-14 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 flex items-center justify-center mx-auto">
            <Mail className="w-7 h-7" />
          </div>

          <div className="space-y-2">
            <h2 className="text-white text-xl font-bold tracking-tight">Check your email</h2>
            <p className="text-white/60 text-sm leading-relaxed">
              We've sent a verification link to <span className="text-white font-medium">{registeredEmail}</span>.
              Please click the link in your email to verify your account and log in.
            </p>
          </div>

          {checkScreenResendSuccess ? (
            <div className="p-3.5 bg-emerald-500/10 border border-emerald-500/20 rounded-xl text-xs text-emerald-400 flex items-center justify-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              <span>Verification email sent! Check your inbox.</span>
            </div>
          ) : (
            <button
              type="button"
              onClick={handleCheckScreenResend}
              disabled={checkScreenResendLoading}
              className="w-full inline-flex items-center justify-center gap-2 py-2.5 px-4 bg-white/10 hover:bg-white/15 border border-white/15 text-white text-xs font-semibold rounded-xl transition-all cursor-pointer"
            >
              {checkScreenResendLoading ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <RefreshCw className="w-3.5 h-3.5" />
              )}
              <span>Resend Verification Email</span>
            </button>
          )}

          <div className="pt-4 border-t border-white/10">
            <button
              type="button"
              onClick={() => {
                setRegisteredEmail(null);
                setTab('login');
                setLoginEmail(registeredEmail);
              }}
              className="text-white/50 hover:text-white text-xs font-semibold transition-colors cursor-pointer"
            >
              ← Back to Sign In
            </button>
          </div>
        </div>
      </div>
    );

    if (isModal) return checkEmailCard;
    return (
      <div className="min-h-screen bg-gradient-to-br from-[#0A0A0A] via-[#111111] to-[#1a1a2e] flex items-center justify-center px-4">
        {checkEmailCard}
      </div>
    );
  }

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
                  setIsUnverifiedError(false);
                  setLoginResendSuccess(false);
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
                <div className={`text-sm rounded-xl p-4 border space-y-3 ${
                  isUnverifiedError
                    ? 'bg-amber-500/10 border-amber-500/30 text-amber-300'
                    : 'bg-red-500/10 border-red-500/30 text-red-400'
                }`}>
                  <div className="flex items-start gap-2.5">
                    <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                    <span className="flex-1">{loginError}</span>
                  </div>

                  {isUnverifiedError && (
                    <div className="pt-2 border-t border-amber-500/20">
                      {loginResendSuccess ? (
                        <div className="flex items-center gap-1.5 text-xs text-emerald-400 font-medium">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          <span>Verification email sent! Check your inbox.</span>
                        </div>
                      ) : (
                        <button
                          type="button"
                          onClick={handleLoginResendVerification}
                          disabled={loginResendLoading}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-amber-500/20 hover:bg-amber-500/30 text-amber-200 text-xs font-semibold rounded-lg transition-colors cursor-pointer"
                        >
                          {loginResendLoading ? (
                            <Loader2 className="w-3 h-3 animate-spin" />
                          ) : (
                            <RefreshCw className="w-3 h-3" />
                          )}
                          <span>Resend Verification Email</span>
                        </button>
                      )}
                    </div>
                  )}
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

              <button
                type="button"
                id="btn-forgot-password"
                onClick={() => setShowForgot(true)}
                className="w-full text-white/40 hover:text-white/70 text-xs py-1 transition-colors cursor-pointer"
              >
                Forgot your password?
              </button>
            </form>
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
                You'll receive a verification email after registering.
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

// ─── Forgot Password Panel ────────────────────────────────────────────────────

import { apiRequestPasswordReset, apiResetPassword } from '../services/authService';

function ForgotPasswordPanel({ onBack }: { onBack: () => void }) {
  const [step, setStep] = useState<'request' | 'reset' | 'done'>('request');
  const [email, setEmail] = useState('');
  const [token, setToken] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [info, setInfo] = useState('');

  const handleRequest = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await apiRequestPasswordReset(email);
      setInfo('If an account exists, a reset token has been sent to your email.');
      setStep('reset');
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (newPassword !== confirm) { setError('Passwords do not match'); return; }
    setLoading(true);
    try {
      await apiResetPassword(token, newPassword);
      setStep('done');
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#0A0A0A] via-[#111111] to-[#1a1a2e] flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        <div className="bg-white/5 border border-white/10 rounded-2xl backdrop-blur-md p-8 shadow-2xl">
          <button onClick={onBack} className="text-white/40 hover:text-white/70 text-sm mb-6 flex items-center gap-2 transition-colors">
            ← Back to Sign In
          </button>

          {step === 'request' && (
            <>
              <h2 className="text-white text-lg font-semibold mb-1">Reset your password</h2>
              <p className="text-white/40 text-sm mb-6">Enter your account email and we'll send a reset token.</p>
              <form onSubmit={handleRequest} className="space-y-4">
                <input
                  id="forgot-email"
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="engineer@company.com"
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white text-sm placeholder-white/20 focus:outline-none focus:border-white/30 transition-all"
                />
                {error && <p className="text-red-400 text-sm">{error}</p>}
                <button
                  id="btn-forgot-submit"
                  type="submit"
                  disabled={loading}
                  className="w-full bg-white text-[#0A0A0A] font-semibold py-3 rounded-xl text-sm hover:bg-white/90 disabled:opacity-50 transition-all"
                >
                  {loading ? 'Sending…' : 'Send Reset Token'}
                </button>
              </form>
            </>
          )}

          {step === 'reset' && (
            <>
              <h2 className="text-white text-lg font-semibold mb-1">Enter new password</h2>
              {info && <p className="text-emerald-400 text-sm mb-4">{info}</p>}
              <form onSubmit={handleReset} className="space-y-4">
                <input
                  id="reset-token"
                  type="text"
                  required
                  value={token}
                  onChange={(e) => setToken(e.target.value)}
                  placeholder="Paste your reset token here"
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white text-sm placeholder-white/20 focus:outline-none focus:border-white/30 transition-all font-mono"
                />
                <input
                  id="reset-new-password"
                  type="password"
                  required
                  minLength={6}
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="New password"
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white text-sm placeholder-white/20 focus:outline-none focus:border-white/30 transition-all"
                />
                <input
                  id="reset-confirm-password"
                  type="password"
                  required
                  value={confirm}
                  onChange={(e) => setConfirm(e.target.value)}
                  placeholder="Confirm new password"
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white text-sm placeholder-white/20 focus:outline-none focus:border-white/30 transition-all"
                />
                {error && <p className="text-red-400 text-sm">{error}</p>}
                <button
                  id="btn-reset-submit"
                  type="submit"
                  disabled={loading}
                  className="w-full bg-white text-[#0A0A0A] font-semibold py-3 rounded-xl text-sm hover:bg-white/90 disabled:opacity-50 transition-all"
                >
                  {loading ? 'Resetting…' : 'Reset Password'}
                </button>
              </form>
            </>
          )}

          {step === 'done' && (
            <div className="text-center py-4">
              <div className="text-4xl mb-4">✅</div>
              <h2 className="text-white text-lg font-semibold mb-2">Password updated!</h2>
              <p className="text-white/40 text-sm mb-6">You can now sign in with your new password.</p>
              <button
                onClick={onBack}
                className="bg-white text-[#0A0A0A] font-semibold py-3 px-8 rounded-xl text-sm hover:bg-white/90 transition-all"
              >
                Sign In
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
