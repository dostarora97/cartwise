"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { useAuth } from "@/lib/auth";
import { Icon } from "@/components/icon";

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

  async function handleGoogleLogin() {
    await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: `${window.location.origin}/auth/callback`,
      },
    });
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-6">
      <h1 className="text-2xl font-bold tracking-heading uppercase">
        CartWise
      </h1>

      <button
        onClick={handleGoogleLogin}
        className="mt-12 flex w-full max-w-sm items-center justify-center gap-3 border border-black px-6 py-4 text-sm font-medium tracking-label uppercase hover:bg-gray-800 hover:text-white transition-colors"
      >
        <Icon name="login" size={20} />
        Auth via Google
      </button>
    </div>
  );
}
