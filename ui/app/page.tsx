"use client";

import { useAuth } from "@/lib/auth";
import { TopBar } from "@/components/top-bar";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

export default function HomePage() {
  const { session, appUser, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (loading) return;
    if (!session) {
      router.replace("/login");
    } else if (!appUser) {
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

  if (!session || !appUser) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-muted-foreground border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col">
      <TopBar />
      <main className="flex-1 p-6">
        <h2 className="text-xl font-semibold">Welcome, {appUser.name}</h2>
        <p className="text-sm text-muted-foreground">
          Your meal plan and splits will appear here.
        </p>
      </main>
    </div>
  );
}
