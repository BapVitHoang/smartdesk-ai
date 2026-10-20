export type TabType = 'chat' | 'ticket' | 'agent' | 'knowledge';

export type UIState = 'success' | 'loading' | 'empty' | 'error';
export type DemoState = UIState;

export type ToastType = 'success' | 'error' | 'info' | 'warning' | 'loading' | 'empty';

export interface Toast {
  id: string;
  message: string;
  type: ToastType;
}

export interface ApiProblemDetails {
  type?: string;
  title: string;
  status: number;
  detail: string;
  instance?: string;
  code?: string;
  invalid_params?: Array<{ name: string; reason: string }>;
}
