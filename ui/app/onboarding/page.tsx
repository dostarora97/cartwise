"use client";

import { Suspense, useState, useEffect, useRef } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import apiClient from "@/lib/api/client";
import { useAuth } from "@/lib/auth";

function OnboardingContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { session, loading, refreshAppUser } = useAuth();

  const swParam = searchParams.get("splitwise");
  const initialStatus = swParam === "success" ? "done" : swParam === "error" ? "connecting" : "loading";

  const [error, setError] = useState(swParam === "error" ? "Failed to connect Splitwise. Please try again." : "");
  const [status, setStatus] = useState<"loading" | "connecting" | "done">(initialStatus);
  const startedRef = useRef(false);

  useEffect(() => {
    if (loading) return;
    if (!session) {
      router.replace("/login");
    }
  }, [loading, session, router]);

  useEffect(() => {
    if (swParam === "success") {
      refreshAppUser().then(() => router.replace("/meal-plan"));
    }
  }, [swParam, refreshAppUser, router]);

  useEffect(() => {
    if (!session || startedRef.current || swParam) return;
    startedRef.current = true;

    async function run() {
      const accessToken = session!.access_token;

      await apiClient.POST("/api/v1/auth/onboard", {
        headers: { Authorization: `Bearer ${accessToken}` },
      });

      const { data: me } = await apiClient.GET("/api/v1/auth/me", {
        headers: { Authorization: `Bearer ${accessToken}` },
      });

      if (me && (me as unknown as { splitwise_connected: boolean }).splitwise_connected) {
        router.replace("/meal-plan");
        return;
      }

      setStatus("connecting");
      const { data, error: apiError } = await apiClient.POST(
        "/api/v1/auth/splitwise/connect",
        { headers: { Authorization: `Bearer ${accessToken}` } },
      );

      if (apiError || !data) {
        setError("Failed to start Splitwise connection.");
        return;
      }

      window.location.href = data.authorize_url;
    }

    run();
  }, [session, swParam, router]);

  async function handleRetry() {
    if (!session) return;
    setError("");
    setStatus("connecting");

    const { data, error: apiError } = await apiClient.POST(
      "/api/v1/auth/splitwise/connect",
      { headers: { Authorization: `Bearer ${session.access_token}` } },
    );

    if (apiError || !data) {
      setError("Failed to start Splitwise connection.");
      return;
    }

    window.location.href = data.authorize_url;
  }

  if (loading || !session) return null;

  return (
    <div className="flex min-h-dvh flex-col">
      <header className="flex items-center justify-center p-3 border-b border-black">
        <span className="text-2xl font-bold tracking-heading uppercase leading-6">
          CartWise
        </span>
      </header>

      <div className="flex flex-1 flex-col items-center justify-center p-3">
        {status === "loading" && (
          <p className="text-sm tracking-wider text-gray-600">Setting up your account...</p>
        )}

        {status === "connecting" && !error && (
          <p className="text-sm tracking-wider text-gray-600">Connecting to Splitwise...</p>
        )}

        {error && (
          <div className="flex flex-col items-center gap-4">
            <p className="text-xs text-red-600 tracking-wider">{error}</p>
            <button
              type="button"
              onClick={handleRetry}
              className="flex items-center justify-center border-2 border-black px-6 py-3 text-base font-bold tracking-label uppercase"
            >
              Try Again
            </button>
          </div>
        )}

        {status === "done" && (
          <p className="text-sm tracking-wider text-gray-600">Connected! Redirecting...</p>
        )}
      </div>
    </div>
  );
}

export default function OnboardingPage() {
  return (
    <Suspense fallback={<div className="flex min-h-dvh items-center justify-center"><p className="text-sm tracking-wider text-gray-600">Loading...</p></div>}>
      <OnboardingContent />
    </Suspense>
  );
}
