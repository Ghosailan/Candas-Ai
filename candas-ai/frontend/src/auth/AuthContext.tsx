import type { ReactNode } from 'react';
import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { apiFetch } from '../api/client';

type AuthUser = {
  id: string;
  org_id: string;
  email: string;
  name: string;
  role: string;
};

type AuthContextValue = {
  token: string | null;
  user: AuthUser | null;
  login: (payload: {
    email: string;
    name: string;
    role: string;
    org_name?: string;
    organisation?: string;
    organization?: string;
  }) => Promise<void>;
  logout: () => void;
};

type LocalTokenEnvelope = {
  status?: string;
  data?: {
    access_token?: string;
    token_type?: string;
    user?: AuthUser;
  };
  access_token?: string;
  token_type?: string;
  user?: AuthUser;
};

const TOKEN_KEY = 'agentic-token';
const USER_KEY = 'agentic-user';

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

function fallbackUser(payload: {
  email: string;
  name: string;
  role: string;
}): AuthUser {
  return {
    id: 'local-user',
    org_id: 'local-org',
    email: payload.email,
    name: payload.name,
    role: payload.role,
  };
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<AuthUser | null>(null);

  useEffect(() => {
    setToken(localStorage.getItem(TOKEN_KEY));

    const savedUser = localStorage.getItem(USER_KEY);
    setUser(savedUser ? JSON.parse(savedUser) : null);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      token,
      user,

      async login(payload) {
        const requestBody = {
          email: payload.email,
          name: payload.name,
          role: payload.role,
          organisation:
            payload.organisation ||
            payload.organization ||
            payload.org_name ||
            'AgenticAI',
          organization:
            payload.organization ||
            payload.organisation ||
            payload.org_name ||
            'AgenticAI',
          org_name:
            payload.org_name ||
            payload.organisation ||
            payload.organization ||
            'AgenticAI',
        };

        const response = await apiFetch<LocalTokenEnvelope>('/auth/local-token', {
          method: 'POST',
          body: JSON.stringify(requestBody),
        });

        const accessToken =
          response.data?.access_token ??
          response.access_token;

        if (!accessToken) {
          console.error('Local auth response did not include access_token:', response);
          throw new Error('No access token returned from local auth endpoint');
        }

        const authUser =
          response.data?.user ??
          response.user ??
          fallbackUser(payload);

        localStorage.setItem(TOKEN_KEY, accessToken);
        localStorage.setItem(USER_KEY, JSON.stringify(authUser));

        setToken(accessToken);
        setUser(authUser);
      },

      logout() {
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(USER_KEY);
        setToken(null);
        setUser(null);
      },
    }),
    [token, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }

  return context;
}