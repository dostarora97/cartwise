"use client";

import { useRouter } from "next/navigation";
import { ChevronLeft } from "lucide-react";

interface TopBarProps {
  showBack?: boolean;
  rightAction?: React.ReactNode;
}

export function TopBar({ showBack = false, rightAction }: TopBarProps) {
  const router = useRouter();

  return (
    <header className="flex h-14 items-center justify-between border-b border-black px-4">
      <div className="w-10">
        {showBack && (
          <button onClick={() => router.back()}>
            <ChevronLeft className="h-5 w-5" />
          </button>
        )}
      </div>

      <span className="text-sm font-bold tracking-[0.3em] uppercase">
        CartWise
      </span>

      <div className="w-10 flex justify-end">{rightAction}</div>
    </header>
  );
}
