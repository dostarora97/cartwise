"use client";

import { useAuth } from "@/lib/auth";
import { Spinner } from "@/components/spinner";
import { ViewTransition } from "react";
import { usePathname } from "next/navigation";

export default function AuthenticatedLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { appUser, loading, error, refreshAppUser } = useAuth();
  const pathname = usePathname();

  if (loading || (!appUser && !error)) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center">
        <Spinner />
      </div>
    );
  }

  if (error || !appUser) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-4 p-3">
        <p className="text-xs text-red-600 tracking-wider">
          Something went wrong.
        </p>
        <button
          onClick={refreshAppUser}
          className="border-2 border-black px-6 py-3 text-base font-bold tracking-label uppercase"
        >
          Try Again
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col">
      <ViewTransition
        key={pathname}
        enter={{
          "nav-forward": "slide-forward",
          "nav-back": "slide-back",
          default: "none",
        }}
        exit={{
          "nav-forward": "slide-forward",
          "nav-back": "slide-back",
          default: "none",
        }}
        default="none"
      >
        {children}
      </ViewTransition>
    </div>
  );
}
