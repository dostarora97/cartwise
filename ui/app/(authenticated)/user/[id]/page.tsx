"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter, useParams } from "next/navigation";
import { useRequiredAuth } from "@/lib/auth";
import apiClient from "@/lib/api/client";
import { type ApiError, toApiError } from "@/lib/errors";
import { TopBar } from "@/components/top-bar";
import { Icon } from "@/components/icon";
import { ErrorBody } from "@/components/error-body";
import { ConfirmDeleteDialog } from "@/components/confirm-delete-dialog";

export default function UserPage() {
  const { appUser, signOut, refreshAppUser } = useRequiredAuth();
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [signingOut, setSigningOut] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [disconnecting, setDisconnecting] = useState<string | null>(null);
  const [confirmDisconnect, setConfirmDisconnect] = useState<string | null>(null);
  const settingsRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (params.id !== appUser.id) {
      router.replace("/me");
    }
  }, [params.id, appUser.id, router]);

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
    setError(null);

    const { error: apiError, response } = await apiClient.DELETE("/api/v1/auth/me", {
      body: { action: "delete" },
    });

    if (apiError) {
      setError(toApiError("Failed to delete account", response));
      setDeleting(false);
      return;
    }

    await signOut();
    router.replace("/login");
  }

  async function handleDisconnect(provider: string) {
    if (provider !== "swiggy") return;
    setDisconnecting(provider);

    try {
      const { error: apiError, response } = await apiClient.POST(
        "/api/v1/auth/swiggy/disconnect",
      );

      if (apiError) {
        setError(toApiError(`Failed to disconnect ${provider}`, response));
        return;
      }
      await refreshAppUser();
    } catch (e) {
      setError({ message: e instanceof Error ? e.message : `Failed to disconnect ${provider}` });
    } finally {
      setDisconnecting(null);
      setConfirmDisconnect(null);
    }
  }

  async function handleConnect(provider: string) {
    try {
      let data;
      let response;

      if (provider === "swiggy") {
        const result = await apiClient.POST("/api/v1/auth/swiggy/connect");
        data = result.data;
        response = result.response;
        if (result.error) {
          setError(toApiError(`Failed to connect ${provider}`, response));
          return;
        }
        document.cookie = `swiggy_code_verifier=${data!.code_verifier}; path=/; max-age=600; SameSite=Lax`;
      } else {
        const result = await apiClient.POST("/api/v1/auth/splitwise/connect");
        data = result.data;
        response = result.response;
        if (result.error) {
          setError(toApiError(`Failed to connect ${provider}`, response));
          return;
        }
      }

      window.location.href = data!.authorize_url;
    } catch (e) {
      setError({ message: e instanceof Error ? e.message : `Failed to connect ${provider}` });
    }
  }

  if (params.id !== appUser.id) return null;

  const connections = [
    { id: "swiggy", label: "Swiggy", connected: appUser.swiggy_connected },
    { id: "splitwise", label: "Splitwise", connected: appUser.splitwise_connected },
  ];

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
          className="flex h-12 w-12 shrink-0 items-center justify-center bg-black disabled:bg-neutral-400"
        >
          {signingOut ? <div className="size-5 animate-spin rounded-full border-[3px] border-white border-t-transparent" /> : <Icon name="logout" size={24} className="text-white translate-x-px" />}
        </button>
      </div>

      <main className="flex flex-1 flex-col p-3">
        <p className="text-sm text-gray-600">{appUser.email}</p>

        {/* Connections section */}
        <div className="mt-3">
          <div className="border border-gray-200">
            {connections.map((conn) => (
              <div
                key={conn.id}
                className="flex items-center h-12 px-3 border-b border-gray-200 last:border-b-0"
              >
                <span className="flex-1 text-sm tracking-wider">
                  {conn.label}
                </span>
                {disconnecting === conn.id ? (
                  <div className="size-4 animate-spin rounded-full border-2 border-black border-t-transparent" />
                ) : (
                  <button
                    onClick={() =>
                      conn.connected
                        ? setConfirmDisconnect(conn.id)
                        : handleConnect(conn.id)
                    }
                    aria-label={`${conn.connected ? "Disconnect" : "Connect"} ${conn.label}`}
                    className={`relative w-10 h-5 rounded-full transition-colors ${
                      conn.connected ? "bg-black" : "bg-gray-300"
                    }`}
                  >
                    <span
                      className={`absolute top-0.5 left-0.5 size-4 rounded-full bg-white transition-transform ${
                        conn.connected ? "translate-x-5" : "translate-x-0"
                      }`}
                    />
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>

        {error && (
          <div className="mt-3">
            <ErrorBody
              message={error.message}
              requestId={error.requestId}
              traceId={error.traceId}
              status={error.status}
            />
          </div>
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

      {/* Disconnect confirmation dialog */}
      {confirmDisconnect && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white border border-black p-6 mx-6 max-w-sm w-full">
            <p className="text-base font-bold tracking-label uppercase mb-4">
              Disconnect {connections.find((c) => c.id === confirmDisconnect)?.label}?
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => handleDisconnect(confirmDisconnect)}
                className="flex-1 h-12 border border-black text-base font-bold tracking-label uppercase"
              >
                Yes
              </button>
              <button
                onClick={() => setConfirmDisconnect(null)}
                className="flex-1 h-12 bg-black text-white text-base font-bold tracking-label uppercase"
              >
                No
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
