"use client";

import { Suspense, useState, useEffect, useRef, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import apiClient from "@/lib/api/client";
import { type ApiError, toApiError } from "@/lib/errors";
import { useAuth } from "@/lib/auth";
import { ErrorBody } from "@/components/error-body";

function OnboardingContent() {
  const searchParams = useSearchParams();
  const { session, loading } = useAuth();

  const swParam = searchParams.get("splitwise");
  const [error, setError] = useState<ApiError | null>(
    swParam === "error" ? { message: "Failed to connect Splitwise. Please try again." } : null,
  );
  const [connecting, setConnecting] = useState(!swParam);
  const startedRef = useRef(false);

  const doConnect = useCallback(async () => {
    await apiClient.POST("/api/v1/auth/onboard");

    const { data, error: apiError, response } = await apiClient.POST(
      "/api/v1/auth/splitwise/connect",
    );

    if (apiError || !data) {
      setError(toApiError("Failed to start Splitwise connection", response));
      setConnecting(false);
      return;
    }

    window.location.href = data.authorize_url;
  }, []);

  useEffect(() => {
    if (loading || !session || swParam || startedRef.current) return;
    startedRef.current = true;
    void (async () => {
      await doConnect();
    })();
  }, [loading, session, swParam, doConnect]);

  function handleRetry() {
    if (!session) return;
    setError(null);
    setConnecting(true);
    void doConnect();
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
          <ErrorBody
            message={error.message}
            requestId={error.requestId}
            traceId={error.traceId}
            status={error.status}
            onRetry={handleRetry}
          />
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
