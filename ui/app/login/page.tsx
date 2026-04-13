"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Auth } from "@supabase/auth-ui-react";
import { ThemeSupa } from "@supabase/auth-ui-shared";
import { createClient } from "@/lib/supabase/client";
import { useAuth } from "@/lib/auth";

export default function LoginPage() {
  const supabase = createClient();
  const { session, appUser, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (loading) return;
    if (session && appUser) {
      router.replace("/");
    } else if (session && !appUser) {
      router.replace("/onboarding");
    }
  }, [session, appUser, loading, router]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-muted-foreground border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center p-6">
      <div className="w-full max-w-sm space-y-8">
        <div className="text-center">
          <h1 className="text-3xl font-semibold tracking-tight">CartWise</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Grocery cost splitting with meal planning
          </p>
        </div>
        <Auth
          supabaseClient={supabase}
          appearance={{
            theme: ThemeSupa,
            variables: {
              default: {
                colors: {
                  brand: "hsl(0 0% 90%)",
                  brandAccent: "hsl(0 0% 80%)",
                },
              },
            },
          }}
          theme="dark"
          providers={["google"]}
          onlyThirdPartyProviders
          redirectTo={`${typeof window !== "undefined" ? window.location.origin : ""}/auth/callback`}
        />
      </div>
    </div>
  );
}
