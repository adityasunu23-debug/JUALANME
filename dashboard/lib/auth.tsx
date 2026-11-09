"use client";

import { useRouter } from "next/navigation";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import { api, getToken, setToken } from "@/lib/api";

export type AdminProfile = {
  id: number;
  telegram_id: number;
  username?: string | null;
  first_name?: string | null;
  last_name?: string | null;
  photo_url?: string | null;
  role: string;
  is_active: boolean;
  permissions: string[];
};

type TokenResponse = {
  access_token: string;
  token_type: string;
  expires_in: number;
  admin: AdminProfile;
};

type TelegramAuthPayload = {
  id: number;
  first_name?: string;
  last_name?: string;
  username?: string;
  photo_url?: string;
  auth_date: number;
  hash: string;
};

type AuthContextValue = {
  admin: AdminProfile | null;
  loading: boolean;
  loginDev: (telegramId: number) => Promise<void>;
  loginTelegram: (payload: TelegramAuthPayload) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
  has: (permission: string) => boolean;
  isOwner: boolean;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [admin, setAdmin] = useState<AdminProfile | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    if (!getToken()) {
      setAdmin(null);
      setLoading(false);
      return;
    }
    try {
      const profile = await api<AdminProfile>("/auth/me");
      setAdmin(profile);
    } catch {
      setToken(null);
      setAdmin(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
    const onStorage = (event: StorageEvent) => {
      if (event.key === "store_admin_token" && !event.newValue) {
        setAdmin(null);
        router.replace("/login");
      }
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, [refresh, router]);

  const applyToken = useCallback((data: TokenResponse) => {
    setToken(data.access_token);
    setAdmin(data.admin);
  }, []);

  const loginDev = useCallback(
    async (telegramId: number) => {
      const data = await api<TokenResponse>("/auth/dev-login", {
        method: "POST",
        body: { telegram_id: telegramId },
        auth: false,
      });
      applyToken(data);
      router.replace("/dashboard");
    },
    [applyToken, router]
  );

  const loginTelegram = useCallback(
    async (payload: TelegramAuthPayload) => {
      const data = await api<TokenResponse>("/auth/telegram-login", {
        method: "POST",
        body: payload,
        auth: false,
      });
      applyToken(data);
      router.replace("/dashboard");
    },
    [applyToken, router]
  );

  const logout = useCallback(async () => {
    try {
      await api("/auth/logout", { method: "POST" });
    } catch {
      // token may already be invalid
    }
    setToken(null);
    setAdmin(null);
    router.replace("/login");
  }, [router]);

  const has = useCallback(
    (permission: string) => {
      if (!admin) return false;
      if (admin.role === "OWNER") return true;
      return admin.permissions?.includes(permission) || admin.permissions?.includes("*");
    },
    [admin]
  );

  const value = useMemo<AuthContextValue>(
    () => ({
      admin,
      loading,
      loginDev,
      loginTelegram,
      logout,
      refresh,
      has,
      isOwner: admin?.role === "OWNER",
    }),
    [admin, loading, loginDev, loginTelegram, logout, refresh, has]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
