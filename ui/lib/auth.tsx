"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import type { Session, User as SupabaseUser } from "@supabase/supabase-js";
import { createClient } from "@/lib/supabase/client";
import apiClient, { setAuthToken } from "@/lib/api/client";
import { ONBOARDED_COOKIE } from "@/lib/cookies";

interface AppUser {
  id: string;
  email: string;
  name: string;
  avatar_url: string | null;
  splitwise_user_id: number | null;
  splitwise_connected: boolean;
}

interface AuthContextType {
  session: Session | null;
  supabaseUser: SupabaseUser | null;
  appUser: AppUser | null;
  loading: boolean;
  error: boolean;
  signOut: () => Promise<void>;
  refreshAppUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [appUser, setAppUser] = useState<AppUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const supabase = useMemo(() => createClient(), []);

  const fetchAppUser = useCallback(async (accessToken: string) => {
    try {
      setError(false);
      const { data, error: apiError } = await apiClient.GET("/api/v1/auth/me", {
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      if (!apiError && data) {
        setAppUser(data as unknown as AppUser);
      } else {
        setAppUser(null);
        setError(true);
      }
    } catch {
      setAppUser(null);
      setError(true);
    }
  }, []);

  const refreshAppUser = useCallback(async () => {
    if (session?.access_token) {
      await fetchAppUser(session.access_token);
    }
  }, [session, fetchAppUser]);

  useEffect(() => {
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange(async (_event, session) => {
      setSession(session);
      if (session?.access_token) {
        setAuthToken(session.access_token);
        await fetchAppUser(session.access_token);
      } else {
        setAuthToken(null);
        setAppUser(null);
      }
      setLoading(false);
    });

    return () => {
      subscription.unsubscribe();
    };
  }, [supabase, fetchAppUser]);

  const signOut = useCallback(async () => {
    document.cookie = `${ONBOARDED_COOKIE}=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT`;
    await supabase.auth.signOut();
    setAuthToken(null);
    setSession(null);
    setAppUser(null);
  }, [supabase]);

  return (
    <AuthContext.Provider
      value={{
        session,
        supabaseUser: session?.user ?? null,
        appUser,
        loading,
        error,
        signOut,
        refreshAppUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}

export function useRequiredAuth() {
  const context = useAuth();
  if (!context.appUser) {
    throw new Error("useRequiredAuth called outside authenticated layout");
  }
  return { ...context, appUser: context.appUser };
}
