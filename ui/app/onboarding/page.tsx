"use client";

import { Suspense, useState, useEffect, useRef, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import apiClient from "@/lib/api/client";
import { useAuth } from "@/lib/auth";

function OnboardingContent() {
  const searchParams = useSearchParams();
  const { session, loading } = useAuth();

  const swParam = searchParams.get("splitwise");
  const [error, setError] = useState(
    swParam === "error" ? "Failed to connect Splitwise. Please try again." : "",
  );
  const [connecting, setConnecting] = useState(!swParam);
  const startedRef = useRef(false);

  const doConnect = useCallback(async (accessToken: string) => {
    await apiClient.POST("/api/v1/auth/onboard", {
      headers: { Authorization: `Bearer ${accessToken}` },
    });

    const { data, error: apiError } = await apiClient.POST(
      "/api/v1/auth/splitwise/connect",
      { headers: { Authorization: `Bearer ${accessToken}` } },
    );

    if (apiError || !data) {
      setError("Failed to start Splitwise connection.");
      setConnecting(false);
      return;
    }

    window.location.href = data.authorize_url;
  }, []);

  useEffect(() => {
    if (loading || !session || swParam || startedRef.current) return;
    startedRef.current = true;
    const token = session.access_token;
    void (async () => {
      await doConnect(token);
    })();
  }, [loading, session, swParam, doConnect]);

  function handleRetry() {
    if (!session) return;
    setError("");
    setConnecting(true);
    void doConnect(session.access_token);
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
        {error ? (
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
        ) : connecting ? (
          <p className="text-sm tracking-wider text-gray-600">
            Connecting to Splitwise...
          </p>
        ) : null}
      </div>
    </div>
  );
}

export default function OnboardingPage() {
  return (
    <Suspense>
      <OnboardingContent />
    </Suspense>
  );
}
