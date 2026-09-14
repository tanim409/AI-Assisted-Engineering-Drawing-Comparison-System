import React, { useEffect } from 'react';
import { Lock, X, LogIn } from 'lucide-react';

interface AuthToastProps {
  message: string;
  isVisible: boolean;
  onClose: () => void;
  onLoginClick: () => void;
}

export const AuthToast: React.FC<AuthToastProps> = ({
  message,
  isVisible,
  onClose,
  onLoginClick,
}) => {
  useEffect(() => {
    if (isVisible) {
      const timer = setTimeout(() => {
        onClose();
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [isVisible, onClose]);

  if (!isVisible) return null;

  return (
    <div
      id="auth-toast"
      className="fixed top-20 right-5 z-50 max-w-sm w-full bg-[#111111]/95 text-white border border-white/15 rounded-xl shadow-2xl backdrop-blur-md p-4 transition-all duration-300 animate-in slide-in-from-right-8 fade-in flex items-start gap-3"
      role="alert"
    >
      <div className="w-9 h-9 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-400 flex items-center justify-center shrink-0 mt-0.5">
        <Lock className="w-4 h-4" />
      </div>

      <div className="flex-1 min-w-0">
        <p className="text-xs font-semibold text-white/90 leading-tight">
          Authentication Required
        </p>
        <p className="text-xs text-white/60 mt-1 leading-snug">
          {message}
        </p>

        <div className="mt-3 flex items-center gap-2">
          <button
            id="toast-btn-login"
            onClick={() => {
              onClose();
              onLoginClick();
            }}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white text-[#0A0A0A] hover:bg-white/90 text-xs font-semibold rounded-lg transition-colors cursor-pointer"
          >
            <LogIn className="w-3 h-3" />
            <span>Log In</span>
          </button>
          <button
            onClick={onClose}
            className="px-2.5 py-1.5 text-xs font-medium text-white/50 hover:text-white/80 transition-colors cursor-pointer"
          >
            Dismiss
          </button>
        </div>
      </div>

      <button
        onClick={onClose}
        className="text-white/40 hover:text-white/80 transition-colors p-1 rounded-md shrink-0 cursor-pointer"
        aria-label="Close notification"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
};
