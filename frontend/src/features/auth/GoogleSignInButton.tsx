import React, { useEffect, useRef, useState } from 'react';
import { loginWithGoogle } from '../../services/api';
import { User as UserType } from '../../types';

const GOOGLE_CLIENT_ID: string = (import.meta as any).env?.VITE_GOOGLE_CLIENT_ID || '';
const GSI_SCRIPT_SRC = 'https://accounts.google.com/gsi/client';

declare global {
  interface Window {
    google?: any;
  }
}

function loadGoogleIdentityScript(): Promise<void> {
  if (window.google?.accounts?.id) return Promise.resolve();
  return new Promise((resolve, reject) => {
    let script = document.querySelector<HTMLScriptElement>(`script[src="${GSI_SCRIPT_SRC}"]`);
    if (!script) {
      script = document.createElement('script');
      script.src = GSI_SCRIPT_SRC;
      script.async = true;
      script.defer = true;
      document.head.appendChild(script);
    }
    script.addEventListener('load', () => resolve());
    script.addEventListener('error', () => reject(new Error('Google Identity Services failed to load')));
  });
}

interface GoogleSignInButtonProps {
  onSignedIn: (user: UserType) => void;
  onToast?: (msg: string, type?: 'info' | 'success' | 'warning' | 'error') => void;
}

/** OAuth2 sign-in via Google Identity Services; the ID token is verified by the backend (POST /auth/google). */
export const GoogleSignInButton: React.FC<GoogleSignInButtonProps> = ({ onSignedIn, onToast }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [unavailable, setUnavailable] = useState(false);

  useEffect(() => {
    if (!GOOGLE_CLIENT_ID) return;
    let cancelled = false;

    loadGoogleIdentityScript()
      .then(() => {
        if (cancelled || !containerRef.current) return;
        window.google.accounts.id.initialize({
          client_id: GOOGLE_CLIENT_ID,
          callback: async (response: { credential?: string }) => {
            if (!response.credential) return;
            try {
              const auth = await loginWithGoogle(response.credential);
              onSignedIn(auth.user);
              onToast?.(`Đã đăng nhập bằng Google: ${auth.user.full_name}`, 'success');
            } catch (err: any) {
              onToast?.(
                err?.message || 'Đăng nhập Google chưa thành công. Vui lòng thử lại hoặc dùng tài khoản demo.',
                'error'
              );
            }
          },
        });
        window.google.accounts.id.renderButton(containerRef.current, {
          type: 'standard',
          size: 'medium',
          text: 'signin_with',
          shape: 'pill',
          locale: 'vi',
        });
      })
      .catch(() => {
        if (!cancelled) setUnavailable(true);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  if (!GOOGLE_CLIENT_ID || unavailable) return null;
  return <div ref={containerRef} aria-label="Đăng nhập bằng Google" />;
};
