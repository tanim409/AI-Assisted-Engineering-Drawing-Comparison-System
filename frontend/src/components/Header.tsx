import React from 'react';
import { ComparisonResult, AsyncState, ReviewSummary } from '../types/comparison';
import { UploadCloud, LogIn } from 'lucide-react';
import { AccountMenu } from './AccountMenu';
import { useAuth } from '../contexts/AuthContext';

interface HeaderProps {
  result: ComparisonResult | null;
  asyncState: AsyncState;
  reviewSummary?: ReviewSummary | null;
  onResetToUpload: () => void;
  onNavigateToLanding?: () => void;
  onOpenLibrary?: () => void;
  onLoggedOut: () => void;
  /** Opens the AuthPage modal; only shown when user is not authenticated */
  onOpenAuthModal?: (tab?: 'login' | 'register') => void;
  onRequestLogin?: (message?: string) => void;
}

export const Header: React.FC<HeaderProps> = ({
  result,
  asyncState,
  reviewSummary,
  onResetToUpload,
  onNavigateToLanding,
  onOpenLibrary,
  onLoggedOut,
  onOpenAuthModal,
  onRequestLogin,
}) => {
  const { isAuthenticated } = useAuth();

  return (
    <nav
      id="app-header"
      className="shrink-0 pt-2.5 pb-1 px-3 sm:px-6 z-40"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-5 h-14 flex items-center justify-between bg-vanilla/95 backdrop-blur-md rounded-[14px] border border-[#E5E5E5]/80 shadow-[0_10px_36px_-16px_rgba(0,0,0,0.22)]">
        {/* Left: Brand / Project Identity with home navigation */}
        <div
          onClick={onNavigateToLanding}
          className="flex items-center gap-2.5 cursor-pointer group"
          title="Back to Landing Page"
        >
          <div className="w-8 h-8 bg-[#0A0A0A] group-hover:bg-[#171717] rounded-[10px] flex items-center justify-center text-white font-bold text-[13px] shrink-0 select-none shadow-xs transition-colors">
            Δ
          </div>
          <div className="flex flex-col">
            <span className="text-[11px] font-medium tracking-[0.12em] uppercase text-[#737373] leading-none group-hover:text-[#525252] transition-colors">
              {result ? 'CAD Comparison Studio' : 'Engineering Review'}
            </span>
            <span className="text-[15px] font-semibold tracking-tight text-[#0A0A0A] leading-tight">
              {result ? `${result.drawingNumber} · ${result.projectName}` : 'Engineering Drawing Diff'}
            </span>
          </div>
        </div>

        {/* Center / Right: status + actions */}
        <div className="flex items-center gap-3 sm:gap-4">
          <button
            id="btn-nav-home"
            onClick={onNavigateToLanding}
            className="text-xs font-medium text-[#525252] hover:text-[#0A0A0A] px-3 py-1.5 rounded-[9999px] border border-[#E5E5E5] hover:bg-[#FAFAFA] transition-colors cursor-pointer"
          >
            Home
          </button>

          {isAuthenticated && (
            <button
              id="btn-nav-new-comparison"
              onClick={() => {
                onResetToUpload();
                if (onNavigateToLanding) {
                  // Ensure page view is set to 'app' workspace
                  window.dispatchEvent(new CustomEvent('nav:open-comparison'));
                }
              }}
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 bg-[#0A0A0A] hover:bg-[#262626] hover:shadow-[0_8px_20px_-8px_rgba(0,0,0,0.5)] text-white text-xs font-semibold rounded-[9999px] transition-all duration-200 cursor-pointer shadow-xs active:scale-[0.98]"
            >
              <span>New Comparison</span>
            </button>
          )}

          {onOpenLibrary && (
            <button
              id="btn-nav-library"
              onClick={() => {
                if (!isAuthenticated) {
                  onRequestLogin?.('Please log in to access the Drawing Library.');
                } else {
                  onOpenLibrary();
                }
              }}
              className="text-xs font-medium text-[#525252] hover:text-[#0A0A0A] px-3 py-1.5 rounded-[9999px] border border-[#E5E5E5] hover:bg-[#FAFAFA] transition-colors cursor-pointer"
            >
              Drawing Library
            </button>
          )}

          {result && asyncState === 'success' && (
            <div className="hidden md:inline-flex items-center gap-1.5 rounded-full bg-emerald-50 border border-emerald-200 px-3 py-1.5 text-[13px] font-semibold text-emerald-800">
              <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
              <span>VLM Verified</span>
              <span className="font-mono">({result.alignmentScore}% similarity)</span>
            </div>
          )}

          {result && asyncState === 'success' && reviewSummary && (
            <div
              className="hidden md:inline-flex items-center gap-1.5 rounded-full bg-blue-50 border border-blue-200 px-3 py-1.5 text-[13px] font-semibold text-blue-800"
              title={`${reviewSummary.confirmed} confirmed · ${reviewSummary.false_positive} false positives · ${reviewSummary.unreviewed} unreviewed`}
            >
              <span className="w-2 h-2 rounded-full bg-blue-500"></span>
              <span>Reviewed</span>
              <span className="font-mono">
                ({reviewSummary.confirmed + reviewSummary.false_positive}/{reviewSummary.total_changes})
              </span>
            </div>
          )}

          {/* Account menu — only when logged in */}
          {isAuthenticated && <AccountMenu onLoggedOut={onLoggedOut} />}

          {/* Login / Create Account — only when not logged in */}
          {!isAuthenticated && onOpenAuthModal && (
            <div className="flex items-center gap-2">
              <button
                id="btn-header-login"
                onClick={() => onOpenAuthModal('login')}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-[#525252] hover:text-[#0A0A0A] rounded-[9999px] border border-[#E5E5E5] hover:bg-[#FAFAFA] transition-colors cursor-pointer"
              >
                <LogIn className="w-3.5 h-3.5" />
                <span>Login</span>
              </button>
              <button
                id="btn-header-register"
                onClick={() => onOpenAuthModal('register')}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-white bg-[#0A0A0A] hover:bg-[#171717] rounded-[9999px] transition-colors cursor-pointer"
              >
                Create Account
              </button>
            </div>
          )}
        </div>
      </div>
    </nav>
  );
};
