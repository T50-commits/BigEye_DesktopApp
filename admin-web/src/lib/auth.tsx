"use client";

import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from "react";
import { login as apiLogin, setToken, getToken } from "./api";

interface AuthState {
  token: string | null;
  userId: string | null;
  isLoading: boolean;
}

interface AuthContextType extends AuthState {
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    token: null,
    userId: null,
    isLoading: true,
  });

  useEffect(() => {
    // Check if we have a token in sessionStorage (survives page refresh)
    const saved = sessionStorage.getItem("bigeye_admin_token");
    const savedUid = sessionStorage.getItem("bigeye_admin_uid");
    if (saved) {
      setToken(saved);
      setState({ token: saved, userId: savedUid, isLoading: false });
    } else {
      setState((s) => ({ ...s, isLoading: false }));
    }
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const res = await apiLogin(email, password);
    setToken(res.token);
    sessionStorage.setItem("bigeye_admin_token", res.token);
    sessionStorage.setItem("bigeye_admin_uid", res.user_id);
    setState({ token: res.token, userId: res.user_id, isLoading: false });
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    sessionStorage.removeItem("bigeye_admin_token");
    sessionStorage.removeItem("bigeye_admin_uid");
    setState({ token: null, userId: null, isLoading: false });
  }, []);

  return (
    <AuthContext.Provider value={{ ...state, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
