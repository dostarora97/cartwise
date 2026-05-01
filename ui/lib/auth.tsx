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
  avatar_url: string | null;
  splitwise_user_id: number | null;
  splitwise_connected: boolean;
}

interface AuthContextType {
  session: Session | null;
  supabaseUser: SupabaseUser | null;
  appUser: AppUser | null;
  loading: boolean;
  signOut: () => Promise<void>;
  refreshAppUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

let renderCount = 0;

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [appUser, setAppUser] = useState<AppUser | null>(null);
  const [loading, setLoading] = useState(true);

  renderCount++;
  console.log("[AuthProvider] render #" + renderCount, { loading, hasSession: !!session, hasAppUser: !!appUser, sessionUser: session?.user?.email });

  const supabase = useMemo(() => {
    console.log("[AuthProvider] useMemo: creating supabase client");
    return createClient();
  }, []);

  const fetchAppUser = useCallback(async (accessToken: string) => {
    console.log("[AuthProvider] fetchAppUser START, token prefix:", accessToken.substring(0, 20) + "...");
    try {
      const { data, error } = await apiClient.GET("/api/v1/auth/me", {
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      console.log("[AuthProvider] fetchAppUser response:", { hasData: !!data, error: error ?? "none" });
      if (!error && data) {
        setAppUser(data as unknown as AppUser);
      } else {
        setAppUser(null);
      }
    } catch (e) {
      console.log("[AuthProvider] fetchAppUser EXCEPTION:", e);
      setAppUser(null);
    }
  }, []);

  const refreshAppUser = useCallback(async () => {
    console.log("[AuthProvider] refreshAppUser called, hasToken:", !!session?.access_token);
    if (session?.access_token) {
      await fetchAppUser(session.access_token);
    }
  }, [session, fetchAppUser]);

  useEffect(() => {
    console.log("[AuthProvider] useEffect MOUNT: subscribing to onAuthStateChange");
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange(async (_event, newSession) => {
      console.log("[AuthProvider] onAuthStateChange event:", _event, {
        hasSession: !!newSession,
        email: newSession?.user?.email,
        expiresAt: newSession?.expires_at,
      });
      setSession(newSession);
      if (newSession?.access_token) {
        console.log("[AuthProvider] onAuthStateChange: setting token + fetching user");
        setAuthToken(newSession.access_token);
        await fetchAppUser(newSession.access_token);
      } else {
        console.log("[AuthProvider] onAuthStateChange: no session, clearing state");
        setAuthToken(null);
        setAppUser(null);
      }
      console.log("[AuthProvider] onAuthStateChange: setLoading(false)");
      setLoading(false);
    });

    return () => {
      console.log("[AuthProvider] useEffect UNMOUNT: unsubscribing");
      subscription.unsubscribe();
    };
  }, [supabase, fetchAppUser]);

  const signOut = useCallback(async () => {
    console.log("[AuthProvider] signOut called");
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
  console.log("[useAuth] consumed:", { loading: context.loading, hasSession: !!context.session, hasAppUser: !!context.appUser });
  return context;
}
