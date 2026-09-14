import React, { useState } from 'react';
import { Lock, CheckCircle2, AlertCircle, ArrowRight, Loader2 } from 'lucide-react';
import { apiResetPassword } from '../services/authService';

interface ResetPasswordPageProps {
  token: string;
  onOpenLogin: () => void;
}

export const ResetPasswordPage: React.FC<ResetPasswordPageProps> = ({ token, onOpenLogin }) => {
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newPassword.length < 6) {
      setError('Password must be at least 6 characters long.');
      return;
    }
    if (newPassword !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      await apiResetPassword(token, newPassword);
      setSuccess(true);
    } catch (err: any) {
      setError(err?.message || 'Password reset failed. Token may be invalid or expired.');
    } finally {
      setLoading(false);
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
              Reset Password
            </span>
          </div>
        </div>

        {success ? (
          <div className="py-4 flex flex-col items-center text-center space-y-5 animate-in fade-in">
            <div className="w-14 h-14 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-600 flex items-center justify-center">
              <CheckCircle2 className="w-8 h-8" />
            </div>
            <div className="space-y-2">
              <h2 className="text-[22px] font-bold text-[#0A0A0A] tracking-tight">
                Password updated!
              </h2>
              <p className="text-[14px] text-[#525252] leading-relaxed">
                Your password has been reset successfully. You can now log in with your new password.
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
        ) : (
          <div className="space-y-6">
            <div className="space-y-1">
              <h2 className="text-[22px] font-bold text-[#0A0A0A] tracking-tight">
                Choose a new password
              </h2>
              <p className="text-[13px] text-[#525252]">
                Enter your new password below. Must be at least 6 characters.
              </p>
            </div>

            {error && (
              <div className="p-3.5 bg-rose-50 border border-rose-200 rounded-[10px] text-xs text-rose-800 flex items-start gap-2.5">
                <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
                <span>{error}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-[#0A0A0A] mb-1">
                  New Password
                </label>
                <div className="relative">
                  <Lock className="w-4 h-4 text-[#A3A3A3] absolute left-3.5 top-3" />
                  <input
                    type="password"
                    required
                    minLength={6}
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full pl-10 pr-3.5 py-2.5 text-xs bg-[#FAFAFA] border border-[#E5E5E5] rounded-[8px] focus:bg-white focus:outline-none focus:border-[#0A0A0A] text-[#0A0A0A]"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-[#0A0A0A] mb-1">
                  Confirm New Password
                </label>
                <div className="relative">
                  <Lock className="w-4 h-4 text-[#A3A3A3] absolute left-3.5 top-3" />
                  <input
                    type="password"
                    required
                    minLength={6}
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full pl-10 pr-3.5 py-2.5 text-xs bg-[#FAFAFA] border border-[#E5E5E5] rounded-[8px] focus:bg-white focus:outline-none focus:border-[#0A0A0A] text-[#0A0A0A]"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full inline-flex items-center justify-center gap-2 px-6 py-3 bg-[#0A0A0A] hover:bg-[#171717] disabled:opacity-50 text-white text-xs font-semibold rounded-[9999px] transition-all cursor-pointer shadow-sm active:scale-[0.98] mt-2"
              >
                {loading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <ArrowRight className="w-4 h-4" />
                )}
                <span>Reset Password</span>
              </button>
            </form>

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
