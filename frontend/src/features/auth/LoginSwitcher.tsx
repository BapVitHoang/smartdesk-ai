import React, { useState, useEffect } from 'react';
import { User, LogIn, LogOut, ShieldCheck, ArrowLeftRight, Loader2 } from 'lucide-react';
import { GoogleLogin, CredentialResponse } from '@react-oauth/google';
import { User as UserType } from '../../types';
import { loginDemo, loginWithGoogle, logout, getCurrentUser } from '../../services/api';

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
  const isDev = Boolean(import.meta.env.DEV);
  const hasGoogleClientId = Boolean(import.meta.env.VITE_GOOGLE_CLIENT_ID);

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
          `Đã chuyển sang vai trò ${auth.user.role === 'admin' ? 'QUẢN TRỊ VIÊN (Admin)' : 'KHÁCH HÀNG (User)'} (${auth.user.full_name})`,
          'success'
        );
      }
    } catch (err: any) {
      if (onToast) {
        onToast(err?.message || 'Đăng nhập demo thất bại. Vui lòng kiểm tra backend.', 'error');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleGoogleSuccess = async (credentialResponse: CredentialResponse) => {
    if (!credentialResponse.credential) {
      if (onToast) onToast('Không nhận được Google ID Token xác thực.', 'error');
      return;
    }

    setIsLoading(true);
    try {
      const auth = await loginWithGoogle(credentialResponse.credential);
      setUserState(auth.user);
      if (onUserChanged) onUserChanged(auth.user);
      if (onToast) {
        onToast(
          `Đăng nhập Google thành công! Xin chào ${auth.user.full_name} (${auth.user.role === 'admin' ? 'Admin' : 'User'}).`,
          'success'
        );
      }
    } catch (err: any) {
      if (onToast) {
        onToast(err?.message || 'Xác thực Google thất bại trên máy chủ.', 'error');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleGoogleError = () => {
    if (onToast) {
      onToast('Đăng nhập Google bị hủy hoặc gặp sự cố kết nối.', 'warning');
    }
  };

  const handleLogout = () => {
    logout();
    setUserState(null);
    if (onUserChanged) onUserChanged(null);
    if (onToast) onToast('Đã đăng xuất tài khoản.', 'info');
  };

  const avatarSrc = userState?.avatar_url || userState?.picture_url;

  return (
    <div className="flex items-center gap-2 text-xs">
      {isLoading && (
        <div className="flex items-center gap-1 text-slate-500 text-[11px]">
          <Loader2 className="w-3.5 h-3.5 animate-spin text-indigo-600" />
          <span>Đang xác thực...</span>
        </div>
      )}

      {userState ? (
        <div className="flex items-center gap-2 bg-slate-100/90 py-1 px-2.5 rounded-xl border border-slate-200 shadow-2xs">
          {avatarSrc ? (
            <img
              src={avatarSrc}
              alt={userState.full_name}
              className="w-6 h-6 rounded-full object-cover border border-slate-300 shadow-2xs"
              referrerPolicy="no-referrer"
            />
          ) : (
            <div
              className={`w-6 h-6 rounded-full text-white flex items-center justify-center font-bold text-[10px] shadow-2xs ${
                userState.role === 'admin' ? 'bg-indigo-600' : 'bg-emerald-600'
              }`}
            >
              {userState.full_name.charAt(0).toUpperCase()}
            </div>
          )}

          <div className="flex flex-col text-left">
            <span className="font-semibold text-slate-800 leading-tight text-[11px] truncate max-w-[110px]" title={userState.full_name}>
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

          {/* 1-Click Role Switcher (Available in development) */}
          {isDev && (
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
          )}

          <button
            onClick={handleLogout}
            title="Đăng xuất"
            className="p-1 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition-colors cursor-pointer"
          >
            <LogOut className="w-3.5 h-3.5" />
          </button>
        </div>
      ) : (
        <div className="flex items-center gap-2">
          {/* Real Google Identity Services Login */}
          {hasGoogleClientId ? (
            <div className="max-h-[32px] overflow-hidden rounded-lg flex items-center">
              <GoogleLogin
                onSuccess={handleGoogleSuccess}
                onError={handleGoogleError}
                size="small"
                shape="pill"
                text="signin_with"
              />
            </div>
          ) : (
            <button
              onClick={() => {
                if (onToast) {
                  onToast('Chưa cấu hình VITE_GOOGLE_CLIENT_ID trong frontend/.env', 'warning');
                }
              }}
              title="Cần cấu hình VITE_GOOGLE_CLIENT_ID trong frontend/.env"
              className="px-2.5 py-1 rounded-lg bg-white hover:bg-slate-50 text-slate-700 font-medium border border-slate-300 text-xs transition-colors cursor-pointer inline-flex items-center gap-1.5 shadow-2xs"
            >
              <svg className="w-3.5 h-3.5" viewBox="0 0 24 24">
                <path
                  fill="#4285F4"
                  d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                />
                <path
                  fill="#34A853"
                  d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                />
                <path
                  fill="#FBBC05"
                  d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
                />
                <path
                  fill="#EA4335"
                  d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
                />
              </svg>
              <span>Đăng nhập Google</span>
            </button>
          )}

          {/* Development Demo Logins */}
          {isDev && (
            <div className="flex items-center gap-1.5 border-l border-slate-200 pl-2">
              <button
                disabled={isLoading}
                onClick={() => handleDemoLogin('admin@smartdesk.ai')}
                className="px-2 py-1 rounded-lg bg-indigo-50 hover:bg-indigo-100 text-indigo-700 font-medium border border-indigo-200 text-xs transition-colors cursor-pointer inline-flex items-center gap-1"
                title="Đăng nhập tài khoản mẫu Quản trị viên"
              >
                <LogIn className="w-3 h-3 text-indigo-600" />
                <span>Admin</span>
              </button>
              <button
                disabled={isLoading}
                onClick={() => handleDemoLogin('an.nguyen@company.vn')}
                className="px-2 py-1 rounded-lg bg-slate-50 hover:bg-slate-100 text-slate-700 font-medium border border-slate-200 text-xs transition-colors cursor-pointer inline-flex items-center gap-1"
                title="Đăng nhập tài khoản mẫu Khách hàng"
              >
                <User className="w-3 h-3 text-slate-500" />
                <span>User</span>
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
