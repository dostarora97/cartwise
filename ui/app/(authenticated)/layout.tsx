"use client";

import { useAuth } from "@/lib/auth";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

export default function AuthenticatedLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { session, appUser, loading } = useAuth();
  const router = useRouter();
  const [wasAuthed, setWasAuthed] = useState(false);

  useEffect(() => {
    if (loading) return;
    if (!session) {
      router.replace("/login");
    } else if (!appUser) {
      router.replace("/onboarding");
    } else {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setWasAuthed(true);
    }
  }, [session, appUser, loading, router]);

  if (!wasAuthed && (loading || !session || !appUser)) {
    return <div className="flex flex-1 flex-col" />;
  }

  return <div className="flex flex-1 flex-col">{children}</div>;
}
