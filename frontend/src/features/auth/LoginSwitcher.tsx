import React, { useState, useEffect } from 'react';
import { User, LogIn, LogOut, ShieldCheck } from 'lucide-react';
import { User as UserType } from '../../types';
import { loginDemo, logout, getCurrentUser } from '../../services/api';

interface LoginSwitcherProps {
  onUserChanged?: (user: UserType | null) => void;
  onToast?: (msg: string, type?: 'info' | 'success' | 'warning' | 'error') => void;
}

export const LoginSwitcher: React.FC<LoginSwitcherProps> = ({
  onUserChanged,
  onToast,
}) => {
  const [currentUser, setCurrentUser] = useState<UserType | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    // Check current session
    getCurrentUser().then((user) => {
      setCurrentUser(user);
      if (onUserChanged) onUserChanged(user);
    });
  }, []);

  const handleDemoLogin = async (email: string) => {
    setIsLoading(true);
    try {
      const auth = await loginDemo(email);
      setCurrentUser(auth.user);
      if (onUserChanged) onUserChanged(auth.user);
      if (onToast) onToast(`Đăng nhập thành công với vai trò ${auth.user.role.toUpperCase()} (${auth.user.full_name})`, 'success');
    } catch {
      if (onToast) onToast('Đăng nhập demo thất bại. Vui lòng kiểm tra backend.', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const handleLogout = () => {
    logout();
    setCurrentUser(null);
    if (onUserChanged) onUserChanged(null);
    if (onToast) onToast('Đã đăng xuất tài khoản.', 'info');
  };

  return (
    <div className="flex items-center gap-2 text-xs">
      {currentUser ? (
        <div className="flex items-center gap-2 bg-slate-100 py-1 px-2.5 rounded-xl border border-slate-200">
          <div className="w-5 h-5 rounded-full bg-indigo-600 text-white flex items-center justify-center font-bold text-[10px]">
            {currentUser.full_name.charAt(0)}
          </div>
          <div className="flex flex-col text-left">
            <span className="font-semibold text-slate-800 leading-tight">{currentUser.full_name}</span>
            <span className="text-[10px] text-indigo-600 font-mono flex items-center gap-0.5">
              <ShieldCheck className="w-2.5 h-2.5" />
              {currentUser.role.toUpperCase()}
            </span>
          </div>
          <button
            onClick={handleLogout}
            title="Đăng xuất"
            className="p-1 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition-colors ml-1 cursor-pointer"
          >
            <LogOut className="w-3.5 h-3.5" />
          </button>
        </div>
      ) : (
        <div className="flex items-center gap-1.5">
          <button
            disabled={isLoading}
            onClick={() => handleDemoLogin('admin@smartdesk.ai')}
            className="px-2.5 py-1 rounded-lg bg-indigo-50 hover:bg-indigo-100 text-indigo-700 font-medium border border-indigo-200 text-xs transition-colors cursor-pointer inline-flex items-center gap-1"
          >
            <LogIn className="w-3 h-3 text-indigo-600" />
            <span>Demo Admin</span>
          </button>
          <button
            disabled={isLoading}
            onClick={() => handleDemoLogin('an.nguyen@company.vn')}
            className="px-2.5 py-1 rounded-lg bg-slate-50 hover:bg-slate-100 text-slate-700 font-medium border border-slate-200 text-xs transition-colors cursor-pointer inline-flex items-center gap-1"
          >
            <User className="w-3 h-3 text-slate-500" />
            <span>Demo User</span>
          </button>
        </div>
      )}
    </div>
  );
};
