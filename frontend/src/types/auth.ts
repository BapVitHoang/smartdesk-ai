export type UserRole = 'admin' | 'user';

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  picture_url?: string;
  created_at?: string;
}

export interface AuthTokenResponse {
  access_token: string;
  token_type: string;
  expires_in?: number;
  user: User;
}

export interface LoginCredentials {
  email: string;
  password?: string;
  google_id_token?: string;
}

export interface OAuth2LoginRequest {
  provider: 'google' | 'demo';
  token?: string;
  email?: string;
}

export interface TokenRequest {
  grant_type?: string;
  username: string;
  password?: string;
  scope?: string;
}

export interface UserProfileResponse {
  id: number;
  email: string;
  full_name: string;
  role: UserRole;
  workspace_id?: number;
  oauth_provider?: string;
}
