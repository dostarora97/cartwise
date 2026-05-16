"use client";

import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { Icon } from "@/components/icon";

interface TopBarProps {
  showBack?: boolean;
  onBack?: () => void;
  rightAction?: React.ReactNode;
}

export function TopBar({ showBack = false, onBack, rightAction }: TopBarProps) {
  const router = useRouter();
  const { appUser } = useAuth();

  const defaultRight = appUser ? (
    <button
      onClick={() => router.push("/me")}
      aria-label="Profile"
      className="flex h-full w-full items-center justify-center"
    >
      {appUser.avatar_url ? (
        <img
          src={appUser.avatar_url}
          alt=""
          className="h-full w-full object-cover"
        />
      ) : (
        <Icon name="account_circle" size={36} />
      )}
    </button>
  ) : undefined;

  return (
    <header className="flex items-stretch justify-between border-b border-black">
      <div className="shrink-0">
        {showBack ? (
          <button onClick={onBack ?? (() => router.back())} aria-label="Go back" className="flex h-full items-center justify-center p-3 bg-black">
            <Icon name="arrow_back_ios_new" size={24} className="text-white" />
          </button>
        ) : (
          <div className="w-12" />
        )}
      </div>

      <div className="flex items-center gap-1 h-12">
        <img src="/logo-grocery.avif" alt="" width={36} height={36} className="object-contain" />
        <img src="/logo-calculator.avif" alt="" width={36} height={36} className="object-contain" />
        <img src="/logo-pizza.avif" alt="" width={36} height={36} className="object-contain" />
      </div>

      <div className="w-12 shrink-0 flex items-stretch">{rightAction ?? defaultRight}</div>
    </header>
  );
}
