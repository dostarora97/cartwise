"use client";

import { useAuth } from "@/lib/auth";
import { Icon } from "@/components/icon";

export function LogoutButton() {
  const { signOut } = useAuth();

  return (
    <button
      onClick={async () => {
        await signOut();
        window.location.href = "/login";
      }}
      aria-label="Sign out"
      className="flex h-full w-full items-center justify-center"
    >
      <Icon name="logout" size={24} />
    </button>
  );
}
