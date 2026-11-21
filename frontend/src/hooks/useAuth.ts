"use client";

import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  type ReactNode,
} from "react";
import { createElement } from "react";
import type { User } from "@/types";
import * as api from "@/lib/api";

interface AuthState {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState>({
  user: null,
  loading: true,
  login: async () => {},
  register: async () => {},
  logout: () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  // Try to restore session on mount
  useEffect(() => {
    (async () => {
      try {
        const tokens = await api.refreshAccessToken();
        if (tokens) {
          const me = await api.getMe();
          setUser(me);
        }
      } catch {
        // No valid session
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const loginFn = useCallback(async (email: string, password: string) => {
    await api.login(email, password);
    const me = await api.getMe();
    setUser(me);
  }, []);

  const registerFn = useCallback(
    async (email: string, password: string, fullName: string) => {
      await api.register(email, password, fullName);
      const me = await api.getMe();
      setUser(me);
    },
    []
  );

  const logoutFn = useCallback(() => {
    api.logout();
    setUser(null);
  }, []);

  return createElement(
    AuthContext.Provider,
    {
      value: { user, loading, login: loginFn, register: registerFn, logout: logoutFn },
    },
    children
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
