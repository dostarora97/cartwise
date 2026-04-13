"use client";

import { useAuth } from "@/lib/auth";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

export default function AuthenticatedLayout({
  children,
}: {
  children: React.ReactNode;
}) {
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

  if (loading || !session || !appUser) {
    return <div className="flex min-h-screen items-center justify-center" />;
  }

  return <>{children}</>;
}
