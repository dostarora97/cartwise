"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useRequiredAuth } from "@/lib/auth";
import { TopBar } from "@/components/top-bar";
import { Icon } from "@/components/icon";
import { ConfirmDeleteDialog } from "@/components/confirm-delete-dialog";
import apiClient from "@/lib/api/client";

export default function ProfilePage() {
  const { appUser, signOut } = useRequiredAuth();
  const router = useRouter();
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [signingOut, setSigningOut] = useState(false);
  const [error, setError] = useState("");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const settingsRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!settingsOpen) return;
    function handleMouseDown(e: MouseEvent) {
      if (settingsRef.current && !settingsRef.current.contains(e.target as Node)) {
        setSettingsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleMouseDown);
    return () => document.removeEventListener("mousedown", handleMouseDown);
  }, [settingsOpen]);

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

        <div ref={settingsRef} className="mt-auto">
          <button
            onClick={() => setSettingsOpen(!settingsOpen)}
            className="flex w-full items-center h-12 px-3 border border-black cursor-pointer"
          >
            <Icon name="settings" size={20} />
            <span className="ml-2 text-base font-bold tracking-label uppercase">Settings</span>
            <Icon name={settingsOpen ? "expand_less" : "expand_more"} size={24} className="ml-auto" />
          </button>
          {settingsOpen && (
            <div className="flex flex-col gap-3 p-3 border-x border-b border-black">
              <a
                href="https://github.com/dostarora97/cartwise/issues/new/choose"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 bg-black text-white p-3 text-base font-bold tracking-label uppercase h-12"
              >
                <Icon name="open_in_new" size={20} />
                Feedback
              </a>
              <button
                onClick={() => setShowDeleteDialog(true)}
                disabled={signingOut}
                className="flex items-center gap-2 bg-black text-red-400 p-3 text-base font-bold tracking-label uppercase h-12"
              >
                <Icon name="delete" size={20} />
                Delete Account
              </button>
            </div>
          )}
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
