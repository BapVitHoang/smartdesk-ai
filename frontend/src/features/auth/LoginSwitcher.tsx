import React, { useState, useEffect } from 'react';
import { User, LogIn, LogOut, ShieldCheck, ArrowLeftRight } from 'lucide-react';
import { User as UserType } from '../../types';
import { loginDemo, logout, getCurrentUser } from '../../services/api';
import { GoogleSignInButton } from './GoogleSignInButton';

interface LoginSwitcherProps {
  currentUser?: UserType | null;
  onUserChanged?: (user: UserType | null) => void;
  onToast?: (msg: string, type?: 'info' | 'success' | 'warning' | 'error') => void;
}

export const LoginSwitcher: React.FC<LoginSwitcherProps> = ({
  currentUser: propUser,
  onUserChanged,
  onToast,
}) => {
  const [userState, setUserState] = useState<UserType | null>(propUser || null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (propUser !== undefined) {
      setUserState(propUser);
    } else {
      getCurrentUser().then((user) => {
        setUserState(user);
        if (onUserChanged) onUserChanged(user);
      });
    }
  }, [propUser]);

  const handleDemoLogin = async (email: string) => {
    setIsLoading(true);
    try {
      const auth = await loginDemo(email);
      setUserState(auth.user);
      if (onUserChanged) onUserChanged(auth.user);
      if (onToast) {
        onToast(
          `Đã chuyển sang vai trò ${auth.user.role === 'admin' ? 'Quản trị viên' : 'Khách hàng'} (${auth.user.full_name})`,
          'success'
        );
      }
    } catch {
      if (onToast) onToast('Đăng nhập demo thất bại. Vui lòng kiểm tra backend.', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const handleLogout = () => {
    logout();
    setUserState(null);
    if (onUserChanged) onUserChanged(null);
    if (onToast) onToast('Đã đăng xuất tài khoản.', 'info');
  };

  return (
    <div className="flex items-center gap-2 text-xs">
      {userState ? (
        <div className="flex items-center gap-2 bg-slate-100/90 py-1 px-2.5 rounded-xl border border-slate-200">
          <div
            className={`relative w-6 h-6 shrink-0 overflow-hidden rounded-full text-white flex items-center justify-center font-bold text-[10px] shadow-2xs ${
              userState.role === 'admin' ? 'bg-indigo-600' : 'bg-emerald-600'
            }`}
          >
            {userState.full_name.charAt(0)}
            {(userState.avatar_url || userState.picture_url) && (
              <img
                src={userState.avatar_url || userState.picture_url}
                alt=""
                referrerPolicy="no-referrer"
                className="absolute inset-0 h-full w-full object-cover"
                onError={(event) => { event.currentTarget.hidden = true; }}
              />
            )}
          </div>
          <div className="flex flex-col text-left">
            <span className="font-semibold text-slate-800 leading-tight text-[11px] truncate max-w-[110px]">
              {userState.full_name}
            </span>
            <span
              className={`text-[9px] font-mono flex items-center gap-0.5 font-bold ${
                userState.role === 'admin' ? 'text-indigo-600' : 'text-emerald-600'
              }`}
            >
              <ShieldCheck className="w-2.5 h-2.5" />
              {userState.role.toUpperCase()}
            </span>
          </div>

          {/* 1-Click Role Switcher */}
          <button
            disabled={isLoading}
            onClick={() =>
              handleDemoLogin(
                userState.role === 'admin' ? 'an.nguyen@company.vn' : 'admin@smartdesk.ai'
              )
            }
            title={
              userState.role === 'admin'
                ? 'Đổi sang tài khoản Khách hàng (an.nguyen@company.vn)'
                : 'Đổi sang tài khoản Quản trị viên (admin@smartdesk.ai)'
            }
            className="p-1 rounded-lg text-slate-500 hover:text-indigo-600 hover:bg-indigo-50 border border-slate-200 bg-white transition-colors cursor-pointer ml-1 inline-flex items-center gap-1 text-[10px] font-semibold"
          >
            <ArrowLeftRight className="w-3 h-3" />
            <span className="hidden xl:inline">
              {userState.role === 'admin' ? 'Sang User' : 'Sang Admin'}
            </span>
          </button>

          <button
            onClick={handleLogout}
            title="Đăng xuất"
            className="p-1 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition-colors cursor-pointer"
          >
            <LogOut className="w-3.5 h-3.5" />
          </button>
        </div>
      ) : (
        <div className="flex items-center gap-1.5">
          <GoogleSignInButton
            onSignedIn={(user) => {
              setUserState(user);
              if (onUserChanged) onUserChanged(user);
            }}
            onToast={onToast}
          />
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
