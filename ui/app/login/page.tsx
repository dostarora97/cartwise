"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { Icon } from "@/components/icon";
import { ErrorBody } from "@/components/error-body";

function LoginContent() {
  const supabase = createClient();
  const searchParams = useSearchParams();
  const errorParam = searchParams.get("error");
  const [error, setError] = useState(
    errorParam ? "Something went wrong. Please try again." : "",
  );

  async function handleGoogleLogin() {
    setError("");
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: `${window.location.origin}/auth/callback`,
      },
    });
    if (error) {
      setError("Failed to sign in. Please try again.");
    }
  }

  return (
    <div className="flex min-h-dvh flex-col items-center justify-center px-6">
      <h1 className="text-2xl font-bold tracking-heading uppercase">
        CartWise
      </h1>

      <button
        onClick={handleGoogleLogin}
        className="mt-12 flex w-full max-w-sm items-center justify-center gap-3 bg-black px-6 py-4 text-sm font-medium tracking-label uppercase text-white"
      >
        <Icon name="login" size={20} />
        Auth via Google
      </button>

      {error && (
        <div className="mt-4">
          <ErrorBody message={error} />
        </div>
      )}
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense>
      <LoginContent />
    </Suspense>
  );
}
