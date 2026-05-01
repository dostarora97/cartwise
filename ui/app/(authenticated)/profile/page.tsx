"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { TopBar } from "@/components/top-bar";
import { Icon } from "@/components/icon";
import { ConfirmDeleteDialog } from "@/components/confirm-delete-dialog";
import apiClient from "@/lib/api/client";

export default function ProfilePage() {
  const { appUser, signOut } = useAuth();
  const router = useRouter();
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [signingOut, setSigningOut] = useState(false);
  const [error, setError] = useState("");

  if (!appUser) return null;

  async function handleDelete() {
    setDeleting(true);
    setError("");

    const { error: apiError } = await apiClient.DELETE("/api/v1/auth/me", {
      body: { action: "delete" },
    });

    if (apiError) {
      setError("Failed to delete account. Please try again.");
      setDeleting(false);
      return;
    }

    await signOut();
    router.replace("/login");
  }

  return (
    <div className="flex flex-1 flex-col">
      <TopBar showBack onBack={() => router.push("/meal-plan")} />

      <div className="flex h-12 items-center border-b border-black">
        <span className="flex-1 p-3 text-2xl font-bold tracking-label uppercase leading-6">
          {appUser.name}
        </span>
        <button
          onClick={async () => {
            setSigningOut(true);
            await signOut();
            window.location.href = "/login";
          }}
          disabled={signingOut}
          aria-label="Sign out"
          className="flex h-12 w-12 shrink-0 items-center justify-center bg-black"
        >
          {signingOut ? <div className="size-5 animate-spin rounded-full border-[3px] border-white border-t-transparent" /> : <Icon name="logout" size={24} className="text-white translate-x-px" />}
        </button>
      </div>

      <main className="flex flex-1 flex-col p-3">
        <p className="text-sm text-gray-600">{appUser.email}</p>

        <div className="flex items-center gap-2 mt-3">
          <Icon name={appUser.splitwise_connected ? "check_circle" : "cancel"} size={20} className={appUser.splitwise_connected ? "text-green-600" : ""} />
          <span className="text-sm tracking-wider">
            {appUser.splitwise_connected ? "Splitwise connected" : "Splitwise not connected"}
          </span>
        </div>

        {error && (
          <p className="text-xs text-red-600 tracking-wider mt-3">{error}</p>
        )}

        <div className="mt-auto flex flex-col gap-3">
          <button
            onClick={() => setShowDeleteDialog(true)}
            disabled={signingOut}
            className="flex items-center justify-center border border-black p-3 text-base font-bold tracking-label uppercase text-red-600 h-12"
          >
            Delete Account
          </button>
        </div>
      </main>

      {showDeleteDialog && (
        <ConfirmDeleteDialog
          onConfirm={handleDelete}
          onCancel={() => setShowDeleteDialog(false)}
          loading={deleting}
        />
      )}
    </div>
  );
}
