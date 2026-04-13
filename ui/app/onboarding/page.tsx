"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import type { Session } from "@supabase/supabase-js";
import { createClient } from "@/lib/supabase/client";
import apiClient from "@/lib/api/client";
import { Button } from "@/components/ui/button";

export default function OnboardingPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [splitwiseUserId, setSplitwiseUserId] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [session, setSession] = useState<Session | null>(null);
  const [ready, setReady] = useState(false);

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

      const meta = session.user?.user_metadata;
      const googleName = meta?.full_name || meta?.name || "";
      if (googleName && !name) setName(googleName);

      setReady(true);
    });

    // Timeout fallback
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
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-muted-foreground border-t-transparent" />
      </div>
    );
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setSubmitting(true);

    const { error: apiError } = await apiClient.POST(
      "/api/v1/auth/onboard",
      {
        headers: {
          Authorization: `Bearer ${session!.access_token}`,
        },
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

    router.replace("/");
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center p-6">
      <div className="w-full max-w-sm space-y-8">
        <div className="text-center">
          <h1 className="text-3xl font-semibold tracking-tight">CartWise</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Welcome! Set up your account
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <label htmlFor="name" className="text-sm font-medium">
              Name
            </label>
            <input
              id="name"
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              placeholder="Your name"
            />
          </div>

          <div className="space-y-2">
            <label htmlFor="phone" className="text-sm font-medium">
              Phone
            </label>
            <input
              id="phone"
              type="tel"
              required
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              placeholder="10 digit phone number"
              pattern="[0-9]{10}"
              title="Enter a 10 digit phone number"
            />
          </div>

          <div className="space-y-2">
            <label htmlFor="splitwise" className="text-sm font-medium">
              Splitwise User ID
            </label>
            <input
              id="splitwise"
              type="number"
              required
              value={splitwiseUserId}
              onChange={(e) => setSplitwiseUserId(e.target.value)}
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              placeholder="Your Splitwise user ID"
            />
          </div>

          {error && <p className="text-sm text-red-500">{error}</p>}

          <Button
            type="submit"
            className="w-full h-12 text-base font-medium"
            disabled={submitting}
          >
            {submitting ? "Setting up..." : "Complete Setup"}
          </Button>
        </form>
      </div>
    </div>
  );
}
