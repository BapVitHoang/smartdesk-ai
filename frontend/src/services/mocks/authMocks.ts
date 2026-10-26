import { AuthTokenResponse } from '../../types';

export const MOCK_ADMIN_AUTH: AuthTokenResponse = {
  access_token: 'mock-jwt-token-admin-smartdesk',
  token_type: 'bearer',
  expires_in: 86400,
  user: {
    id: 1,
    email: 'admin@smartdesk.ai',
    full_name: 'System Administrator',
    role: 'admin',
    is_active: true,
  },
};

export const MOCK_USER_AUTH: AuthTokenResponse = {
  access_token: 'mock-jwt-token-user-an-nguyen',
  token_type: 'bearer',
  expires_in: 86400,
  user: {
    id: 2,
    email: 'an.nguyen@company.vn',
    full_name: 'Nguyễn Văn An',
    role: 'user',
    is_active: true,
  },
};
