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
  const [phone, setPhone] = useState("");
  const [splitwiseUserId, setSplitwiseUserId] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [session, setSession] = useState<Session | null>(null);
  const [ready, setReady] = useState(false);
  const nameRef = useRef("");

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

      if (!nameRef.current) {
        const meta = session.user?.user_metadata;
        nameRef.current = meta?.full_name || meta?.name || "";
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
          name: nameRef.current,
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
      <header className="flex h-14 items-center justify-center border-b border-black">
        <span className="text-sm font-bold tracking-[0.3em] uppercase">
          CartWise
        </span>
      </header>

      <form onSubmit={handleSubmit} className="flex flex-1 flex-col justify-center px-6">
        <div className="space-y-8">
          <div>
            <label className="text-xs font-bold tracking-[0.2em] uppercase">
              Phone
            </label>
            <input
              type="tel"
              required
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="0000000000"
              pattern="[0-9]{10}"
              className="mt-2 block w-full border-b-2 border-black bg-transparent pb-2 text-base font-medium tracking-wider outline-none placeholder:text-gray-300"
            />
          </div>

          <div>
            <label className="text-xs font-bold tracking-[0.2em] uppercase">
              Splitwise User ID
            </label>
            <input
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

      <div className="sticky bottom-0 border-t border-black bg-white px-6 py-4">
        <button
          onClick={(e) => {
            e.preventDefault();
            document.querySelector("form")?.requestSubmit();
          }}
          disabled={submitting}
          className="w-full bg-black py-4 text-sm font-bold tracking-[0.2em] uppercase text-white disabled:opacity-50"
        >
          {submitting ? "Connecting..." : "Connect to Splitwise"}
        </button>
      </div>
    </div>
  );
}
