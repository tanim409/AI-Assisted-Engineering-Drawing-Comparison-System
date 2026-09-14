/**
 * AccountMenu — user avatar button in the Header that opens a dropdown
 * with account info, settings, and logout / delete-account actions.
 */
import React, { useEffect, useRef, useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { apiDeleteAccount, apiLogout } from '../services/authService';
import { LogOut, Trash2, User, CheckCircle, AlertCircle, ChevronDown } from 'lucide-react';

interface AccountMenuProps {
  /** Called after logout/deletion so the parent can navigate to auth screen */
  onLoggedOut: () => void;
}

export const AccountMenu: React.FC<AccountMenuProps> = ({ onLoggedOut }) => {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState('');
  const [confirmText, setConfirmText] = useState('');
  const menuRef = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false);
        setShowDeleteConfirm(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  if (!user) return null;

  const initials = user.email.slice(0, 2).toUpperCase();

  const handleLogout = () => {
    logout();
    onLoggedOut();
  };

  const handleDeleteAccount = async () => {
    if (confirmText !== 'DELETE') return;
    setDeleting(true);
    setDeleteError('');
    try {
      await apiDeleteAccount();
      logout();
      onLoggedOut();
    } catch (err: any) {
      setDeleteError(err.message || 'Deletion failed');
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div ref={menuRef} className="relative" id="account-menu">
      {/* Trigger */}
      <button
        id="btn-account-menu-trigger"
        onClick={() => { setOpen((p) => !p); setShowDeleteConfirm(false); }}
        className="flex items-center gap-2 px-3 py-1.5 rounded-full border border-[#E5E5E5] hover:bg-[#FAFAFA] transition-colors cursor-pointer"
      >
        <div className="w-6 h-6 rounded-full bg-[#0A0A0A] text-white flex items-center justify-center text-[10px] font-bold shrink-0">
          {initials}
        </div>
        <span className="hidden sm:block text-xs font-medium text-[#525252] max-w-32 truncate">{user.email}</span>
        <ChevronDown className={`w-3 h-3 text-[#A3A3A3] transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {/* Dropdown */}
      {open && (
        <div className="absolute right-0 top-full mt-2 w-72 bg-white border border-[#E5E5E5] rounded-2xl shadow-xl z-50 overflow-hidden animate-in fade-in slide-in-from-top-2 duration-150">
          {!showDeleteConfirm ? (
            <>
              {/* User info header */}
              <div className="px-4 py-3 border-b border-[#F5F5F5]">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-[#0A0A0A] text-white flex items-center justify-center text-sm font-bold shrink-0">
                    {initials}
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-[#0A0A0A] truncate">{user.email}</p>
                    <div className="flex items-center gap-1 mt-0.5">
                      {user.email_verified ? (
                        <>
                          <CheckCircle className="w-3 h-3 text-emerald-500" />
                          <span className="text-[11px] text-emerald-600">Email verified</span>
                        </>
                      ) : (
                        <>
                          <AlertCircle className="w-3 h-3 text-amber-500" />
                          <span className="text-[11px] text-amber-600">Email not verified</span>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="p-2">
                <button
                  id="btn-account-logout"
                  onClick={handleLogout}
                  className="w-full flex items-center gap-3 px-3 py-2.5 text-sm text-[#525252] hover:text-[#0A0A0A] hover:bg-[#FAFAFA] rounded-xl transition-colors text-left cursor-pointer"
                >
                  <LogOut className="w-4 h-4 shrink-0" />
                  Sign out
                </button>
                <button
                  id="btn-account-delete-open"
                  onClick={() => setShowDeleteConfirm(true)}
                  className="w-full flex items-center gap-3 px-3 py-2.5 text-sm text-red-500 hover:text-red-600 hover:bg-red-50 rounded-xl transition-colors text-left cursor-pointer"
                >
                  <Trash2 className="w-4 h-4 shrink-0" />
                  Delete account & data
                </button>
              </div>
            </>
          ) : (
            /* Delete Confirmation */
            <div className="p-4">
              <div className="flex items-center gap-2 mb-3">
                <Trash2 className="w-4 h-4 text-red-500" />
                <h3 className="text-sm font-semibold text-[#0A0A0A]">Delete account</h3>
              </div>
              <p className="text-xs text-[#737373] mb-1">
                This will permanently delete your account and <strong>all drawings, reports, and comparisons</strong>.
                This action cannot be undone.
              </p>
              <p className="text-xs text-[#737373] mb-3">
                Type <span className="font-mono font-bold text-red-500">DELETE</span> to confirm:
              </p>
              <input
                id="delete-account-confirm-input"
                type="text"
                value={confirmText}
                onChange={(e) => setConfirmText(e.target.value)}
                placeholder="Type DELETE to confirm"
                className="w-full border border-red-200 rounded-xl px-3 py-2 text-sm font-mono focus:outline-none focus:border-red-400 mb-3"
              />
              {deleteError && <p className="text-red-500 text-xs mb-2">{deleteError}</p>}
              <div className="flex gap-2">
                <button
                  onClick={() => { setShowDeleteConfirm(false); setConfirmText(''); setDeleteError(''); }}
                  className="flex-1 px-3 py-2 text-xs font-medium text-[#525252] bg-[#F5F5F5] hover:bg-[#E5E5E5] rounded-xl transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  id="btn-account-delete-confirm"
                  onClick={handleDeleteAccount}
                  disabled={confirmText !== 'DELETE' || deleting}
                  className="flex-1 px-3 py-2 text-xs font-medium text-white bg-red-500 hover:bg-red-600
                    disabled:opacity-40 disabled:cursor-not-allowed rounded-xl transition-colors cursor-pointer"
                >
                  {deleting ? 'Deleting…' : 'Delete Everything'}
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
