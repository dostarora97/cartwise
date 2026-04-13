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

interface AppUser {
  id: string;
  email: string;
  name: string;
  phone: string | null;
  avatar_url: string | null;
  splitwise_user_id: number | null;
}

interface AuthContextType {
  session: Session | null;
  supabaseUser: SupabaseUser | null;
  appUser: AppUser | null;
  loading: boolean;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [appUser, setAppUser] = useState<AppUser | null>(null);
  const [loading, setLoading] = useState(true);

  const supabase = useMemo(() => createClient(), []);

  const fetchAppUser = useCallback(async (accessToken: string) => {
    try {
      const { data, error } = await apiClient.GET("/api/v1/auth/me", {
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      if (!error && data) {
        setAppUser(data as unknown as AppUser);
      } else {
        setAppUser(null);
      }
    } catch {
      setAppUser(null);
    }
  }, []);

  useEffect(() => {
    // Use onAuthStateChange as the single source of truth.
    // getUser() and getSession() hang with @supabase/ssr's cookie-based client,
    // but onAuthStateChange fires reliably when the session is detected from cookies.
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

    // Safety timeout: if onAuthStateChange doesn't fire within 3s, stop loading
    const timeout = setTimeout(() => {
      setLoading((prev) => prev ? false : prev);
    }, 3000);

    return () => {
      subscription.unsubscribe();
      clearTimeout(timeout);
    };
  }, [supabase, fetchAppUser]);

  const signOut = useCallback(async () => {
    await supabase.auth.signOut();
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
        signOut,
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
