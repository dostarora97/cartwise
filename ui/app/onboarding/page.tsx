"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import type { Session } from "@supabase/supabase-js";
import { createClient } from "@/lib/supabase/client";
import apiClient from "@/lib/api/client";
import { useAuth } from "@/lib/auth";

export default function OnboardingPage() {
  const router = useRouter();
  const { refreshAppUser } = useAuth();
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [splitwiseUserId, setSplitwiseUserId] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [session, setSession] = useState<Session | null>(null);
  const [ready, setReady] = useState(false);
  const namePrefilledRef = useRef(false);

  useEffect(() => {
    const supabase = createClient();
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      if (!session) {
        router.replace("/login");
        return;
      }
      setSession(session);

      if (!namePrefilledRef.current) {
        const meta = session.user?.user_metadata;
        const googleName = meta?.full_name || meta?.name || "";
        if (googleName) {
          setName(googleName);
          namePrefilledRef.current = true;
        }
      }

      setReady(true);
    });

    const timeout = setTimeout(() => {
      setReady((prev) => {
        if (!prev) router.replace("/login");
        return prev;
      });
    }, 5000);

    return () => {
      subscription.unsubscribe();
      clearTimeout(timeout);
    };
  }, [router]);

  if (!ready) {
    return <div className="flex min-h-screen items-center justify-center" />;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setSubmitting(true);

    const { error: apiError } = await apiClient.POST(
      "/api/v1/auth/onboard",
      {
        headers: { Authorization: `Bearer ${session!.access_token}` },
        body: {
          name,
          phone,
          splitwise_user_id: parseInt(splitwiseUserId, 10),
        },
      },
    );

    if (apiError) {
      setError("Failed to complete setup. Please try again.");
      setSubmitting(false);
      return;
    }

    await refreshAppUser();
    router.replace("/");
  }

  return (
    <div className="flex min-h-screen flex-col">
      <header className="flex items-center justify-center p-3 border-b border-black">
        <span className="text-2xl font-bold tracking-heading uppercase leading-6">
          CartWise
        </span>
      </header>

      <form id="onboarding" onSubmit={handleSubmit} className="flex flex-1 flex-col justify-center p-3">
        <div className="flex flex-col gap-8">
          <div>
            <label htmlFor="onboarding-name" className="text-xs font-bold tracking-label uppercase">
              Name
            </label>
            <input
              id="onboarding-name"
              type="text"
              required
              autoComplete="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Your name"
              className="mt-2 block w-full border-b-2 border-black bg-transparent pb-2 text-base font-medium tracking-wider outline-none placeholder:text-gray-300"
            />
          </div>

          <div>
            <label htmlFor="onboarding-phone" className="text-xs font-bold tracking-label uppercase">
              Phone
            </label>
            <input
              id="onboarding-phone"
              type="tel"
              required
              autoComplete="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="0000000000"
              pattern="[0-9]{10}"
              className="mt-2 block w-full border-b-2 border-black bg-transparent pb-2 text-base font-medium tracking-wider outline-none placeholder:text-gray-300"
            />
          </div>

          <div>
            <label htmlFor="onboarding-splitwise-id" className="text-xs font-bold tracking-label uppercase">
              Splitwise User ID
            </label>
            <input
              id="onboarding-splitwise-id"
              type="number"
              required
              value={splitwiseUserId}
              onChange={(e) => setSplitwiseUserId(e.target.value)}
              placeholder="00000"
              className="mt-2 block w-full border-b-2 border-black bg-transparent pb-2 text-base font-medium tracking-wider outline-none placeholder:text-gray-300"
            />
          </div>
        </div>

        {error && (
          <p className="mt-4 text-xs text-red-600 tracking-wider">{error}</p>
        )}
      </form>

      <button
        type="submit"
        form="onboarding"
        disabled={submitting}
        className="sticky bottom-0 flex w-full items-center justify-center p-3 border-t border-black bg-black text-2xl font-bold tracking-label uppercase leading-6 text-white disabled:opacity-50"
      >
        {submitting ? "Connecting..." : "Connect to Splitwise"}
      </button>
    </div>
  );
}
