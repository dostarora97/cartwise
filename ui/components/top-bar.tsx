"use client";

import { useRouter } from "next/navigation";
import { ChevronLeft } from "lucide-react";
import { useAuth } from "@/lib/auth";

interface TopBarProps {
  showBack?: boolean;
}

export function TopBar({ showBack = false }: TopBarProps) {
  const { appUser } = useAuth();
  const router = useRouter();

  return (
    <header className="sticky top-0 z-50 flex h-14 items-center justify-between border-b border-border/50 bg-background/95 px-4 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="w-10">
        {showBack && (
          <button
            onClick={() => router.back()}
            className="flex h-10 w-10 items-center justify-center rounded-md hover:bg-accent"
          >
            <ChevronLeft className="h-5 w-5" />
          </button>
        )}
      </div>

      <span className="text-lg font-semibold tracking-tight">CartWise</span>

      <div className="w-10">
        {appUser && (
          <button
            onClick={() => router.push(`/profile/${appUser.id}`)}
            className="flex h-10 w-10 items-center justify-center rounded-full hover:bg-accent"
          >
            {appUser.avatar_url ? (
              <img
                src={appUser.avatar_url}
                alt={appUser.name}
                className="h-8 w-8 rounded-full"
              />
            ) : (
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-muted text-sm font-medium">
                {appUser.name.charAt(0).toUpperCase()}
              </div>
            )}
          </button>
        )}
      </div>
    </header>
  );
}
