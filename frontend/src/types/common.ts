export type TabType = 'chat' | 'ticket' | 'agent' | 'knowledge';

export type UIState = 'success' | 'loading' | 'empty' | 'error';
export type DemoState = UIState;

export type ToastType = 'success' | 'error' | 'info' | 'warning' | 'loading' | 'empty';

export interface Toast {
  id: string;
  message: string;
  type: ToastType;
}
