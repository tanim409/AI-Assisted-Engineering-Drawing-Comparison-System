import React, { useEffect, useState } from 'react';
import { CheckCircle2, AlertCircle, Mail, ArrowRight, Loader2, RefreshCw } from 'lucide-react';
import { apiVerifyEmail, apiResendVerification } from '../services/authService';

interface VerifyEmailPageProps {
  token: string;
  onOpenLogin: () => void;
}

export const VerifyEmailPage: React.FC<VerifyEmailPageProps> = ({ token, onOpenLogin }) => {
  const [status, setStatus] = useState<'verifying' | 'success' | 'error'>('verifying');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  
  // Resend form state for error scenario
  const [resendEmail, setResendEmail] = useState('');
  const [resendLoading, setResendLoading] = useState(false);
  const [resendSuccess, setResendSuccess] = useState(false);
  const [resendError, setResendError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    if (!token) {
      setStatus('error');
      setErrorMessage('No verification token provided.');
      return;
    }

    async function verify() {
      try {
        await apiVerifyEmail(token);
        if (isMounted) {
          setStatus('success');
        }
      } catch (err: any) {
        if (isMounted) {
          setStatus('error');
          setErrorMessage(err?.message || 'Invalid or expired verification token.');
        }
      }
    }

    verify();
    return () => {
      isMounted = false;
    };
  }, [token]);

  const handleResend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!resendEmail.trim()) return;
    setResendLoading(true);
    setResendError(null);
    setResendSuccess(false);

    try {
      await apiResendVerification(resendEmail.trim());
      setResendSuccess(true);
    } catch (err: any) {
      setResendError(err?.message || 'Could not send verification email.');
    } finally {
      setResendLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#FAFAFA] text-[#0A0A0A] flex flex-col items-center justify-center p-4 font-sans selection:bg-[#0A0A0A] selection:text-white">
      <div className="w-full max-w-md bg-white border border-[#E5E5E5] rounded-[16px] p-8 shadow-xl">
        {/* Brand header */}
        <div className="flex items-center gap-3 mb-8 pb-6 border-b border-[#F5F5F5]">
          <div className="w-9 h-9 bg-[#0A0A0A] rounded-[8px] flex items-center justify-center text-white font-bold text-sm select-none font-mono">
            Δ
          </div>
          <div className="flex flex-col">
            <span className="text-[11px] font-mono font-semibold uppercase tracking-[0.05em] text-[#6b7280] leading-none">
              Engineering Review
            </span>
            <span className="text-base font-semibold tracking-tight text-[#111827] leading-tight">
              Account Verification
            </span>
          </div>
        </div>

        {/* State 1: Verifying */}
        {status === 'verifying' && (
          <div className="py-8 flex flex-col items-center text-center space-y-4">
            <Loader2 className="w-10 h-10 text-[#0A0A0A] animate-spin" />
            <h2 className="text-[20px] font-bold text-[#0A0A0A] tracking-tight">
              Verifying your email…
            </h2>
            <p className="text-[14px] text-[#525252] max-w-xs">
              Please wait a moment while we validate your verification token.
            </p>
          </div>
        )}

        {/* State 2: Success */}
        {status === 'success' && (
          <div className="py-4 flex flex-col items-center text-center space-y-5 animate-in fade-in">
            <div className="w-14 h-14 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-600 flex items-center justify-center">
              <CheckCircle2 className="w-8 h-8" />
            </div>
            <div className="space-y-2">
              <h2 className="text-[22px] font-bold text-[#0A0A0A] tracking-tight">
                Email verified!
              </h2>
              <p className="text-[14px] text-[#525252] leading-relaxed">
                Your email address has been verified. You can now log in to your account.
              </p>
            </div>
            <button
              onClick={onOpenLogin}
              className="w-full inline-flex items-center justify-center gap-2 px-6 py-3 bg-[#0A0A0A] hover:bg-[#171717] text-white text-[14px] font-semibold rounded-[9999px] transition-all cursor-pointer shadow-sm active:scale-[0.98] mt-2"
            >
              <span>Proceed to Login</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* State 3: Error */}
        {status === 'error' && (
          <div className="py-2 space-y-6 animate-in fade-in">
            <div className="flex items-start gap-3.5 p-4 bg-rose-50 border border-rose-200 rounded-[12px] text-rose-900">
              <AlertCircle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
              <div className="text-xs space-y-1">
                <p className="font-semibold text-rose-950">Verification Failed</p>
                <p className="text-rose-800 leading-relaxed">
                  {errorMessage || 'The verification link is invalid or has expired.'}
                </p>
              </div>
            </div>

            {/* Request a new verification link */}
            <div className="space-y-3 pt-2 border-t border-[#F5F5F5]">
              <h3 className="text-[14px] font-semibold text-[#0A0A0A]">
                Request a new verification email
              </h3>
              <p className="text-[13px] text-[#525252]">
                Enter your email address below and we'll send you a fresh verification link.
              </p>

              {resendSuccess ? (
                <div className="p-3.5 bg-emerald-50 border border-emerald-200 rounded-[10px] text-[13px] text-emerald-800 flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                  <span>Verification link sent! Check your inbox.</span>
                </div>
              ) : (
                <form onSubmit={handleResend} className="space-y-3">
                  {resendError && (
                    <p className="text-xs text-rose-600">{resendError}</p>
                  )}
                  <div className="relative">
                    <Mail className="w-4 h-4 text-[#A3A3A3] absolute left-3.5 top-3" />
                    <input
                      type="email"
                      required
                      value={resendEmail}
                      onChange={(e) => setResendEmail(e.target.value)}
                      placeholder="name@company.com"
                      className="w-full pl-10 pr-3.5 py-2.5 text-xs bg-[#FAFAFA] border border-[#E5E5E5] rounded-[8px] focus:bg-white focus:outline-none focus:border-[#0A0A0A] text-[#0A0A0A]"
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={resendLoading}
                    className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-[#0A0A0A] hover:bg-[#171717] disabled:opacity-50 text-white text-xs font-semibold rounded-[9999px] transition-colors cursor-pointer"
                  >
                    {resendLoading ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <RefreshCw className="w-3.5 h-3.5" />
                    )}
                    <span>Resend Verification Email</span>
                  </button>
                </form>
              )}
            </div>

            <div className="pt-4 border-t border-[#F5F5F5] text-center">
              <button
                type="button"
                onClick={onOpenLogin}
                className="text-xs font-semibold text-[#525252] hover:text-[#0A0A0A] transition-colors cursor-pointer"
              >
                ← Back to Login
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
