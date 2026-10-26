export type UserRole = 'admin' | 'user';

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  workspace_id?: number;
  avatar_url?: string;
  picture_url?: string; // Backwards compatible alias
  created_at?: string;
}

export interface AuthTokenResponse {
  access_token: string;
  token_type: string;
  user: User;
  role?: UserRole;
  email?: string;
  full_name?: string;
  expires_in?: number;
}

export interface LoginCredentials {
  email: string;
  password?: string;
  google_id_token?: string;
}

export interface OAuth2LoginRequest {
  provider: 'google' | 'demo';
  token?: string;
  credential?: string;
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
  avatar_url?: string;
  is_active?: boolean;
}
