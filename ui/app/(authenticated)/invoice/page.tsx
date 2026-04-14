"use client";

import { Suspense, useState, useRef, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { $api } from "@/lib/api/hooks";
import { TopBar } from "@/components/top-bar";
import { ChipInput, type ChipInputHandle } from "@/components/chip-input";
import { Icon } from "@/components/icon";
import { ErrorModal } from "@/components/error-modal";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function InvoiceSetupPage() {
  return (
    <Suspense>
      <InvoiceSetupContent />
    </Suspense>
  );
}

function InvoiceSetupContent() {
  const { appUser, session } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const fileRef = useRef<HTMLInputElement>(null);
  const chipInputRef = useRef<ChipInputHandle>(null);

  const [file, setFile] = useState<File | null>(null);
  const [selectedOthers, setSelectedOthers] = useState<string[]>([]);
  const [showingAll, setShowingAll] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { data: users } = $api.useQuery("get", "/api/v1/users/");
  const otherUsers = (users ?? [])
    .filter((u) => u.id !== appUser?.id)
    .map((u) => ({ id: u.id, name: u.name }));

  // Pick up shared file from Web Share Target (cached by service worker)
  useEffect(() => {
    if (searchParams.get("received") !== "true") return;
    (async () => {
      const cache = await caches.open("shared-files");
      const resp = await cache.match("/shared-invoice");
      if (!resp) return;
      const blob = await resp.blob();
      const name = resp.headers.get("X-File-Name") || "invoice.pdf";
      setFile(new File([blob], name, { type: blob.type }));
      await cache.delete("/shared-invoice");
    })();
  }, [searchParams]);

  async function handleAnalyse() {
    if (!file || !session?.access_token || !appUser || selectedOthers.length === 0) return;
    setSubmitting(true);

    try {
      const participantIds = [appUser!.id, ...selectedOthers];
      const formData = new FormData();
      formData.append("file", file);
      formData.append("participant_ids", JSON.stringify(participantIds));

      const resp = await fetch(`${API_BASE}/api/v1/orders/`, {
        method: "POST",
        headers: { Authorization: `Bearer ${session.access_token}` },
        body: formData,
      });

      if (!resp.ok) {
        const body = await resp.json().catch(() => ({ detail: "Unknown error" }));
        throw new Error(body.detail || `HTTP ${resp.status}`);
      }

      const data = await resp.json();
      router.push(`/invoice/${data.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen flex-col">
      <TopBar showBack onBack={() => router.push("/meal-plan")} />

      <div className="flex items-center p-3 border-b border-black">
        <span className="text-2xl font-bold tracking-label uppercase leading-6">
          Expense
        </span>
      </div>

      <main className="flex-1">
        {/* Participants */}
        <div className="flex items-stretch border-b border-gray-200">
          <div className="flex flex-wrap items-center gap-1 p-3 flex-1 text-base leading-6">
            <span>With <b>You</b>,</span>
            <ChipInput
              ref={chipInputRef}
              participants={otherUsers}
              selected={selectedOthers}
              onAdd={(id) => setSelectedOthers((prev) => [...prev, id])}
              onRemove={(id) => setSelectedOthers((prev) => prev.filter((x) => x !== id))}
              onShowAllChange={setShowingAll}
            />
          </div>
          {otherUsers.length > selectedOthers.length && (
            <button
              type="button"
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => chipInputRef.current?.toggleAll()}
              aria-label="Toggle participant list"
              className="flex items-center justify-center p-3 bg-black text-white"
            >
              <Icon name={showingAll ? "arrow_drop_up" : "arrow_drop_down"} size={24} />
            </button>
          )}
        </div>

        {/* File upload */}
        <div className="flex items-stretch border-b border-gray-200">
          <label className="flex items-center gap-3 p-3 flex-1 cursor-pointer">
            <Icon name={file ? "description" : "upload_file"} size={24} />
            <span className="text-base leading-6 truncate">
              {file ? file.name : "Invoice"}
            </span>
            <input
              ref={fileRef}
              type="file"
              accept=".pdf,application/pdf"
              className="hidden"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
          </label>
          {file && (
            <button
              type="button"
              onClick={() => {
                setFile(null);
                if (fileRef.current) fileRef.current.value = "";
              }}
              aria-label="Remove file"
              className="flex items-center justify-center p-3"
            >
              <Icon name="close" size={24} />
            </button>
          )}
        </div>
      </main>

      {/* Bottom button */}
      <button
        onClick={handleAnalyse}
        disabled={!file || selectedOthers.length === 0 || submitting}
        className="sticky bottom-0 flex w-full items-center justify-center p-3 border-t border-black bg-black text-2xl font-bold tracking-label uppercase leading-6 text-white disabled:opacity-30"
      >
        Add
      </button>

      {submitting && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
          <div className="bg-white border border-black p-3">
            <span className="text-2xl font-bold tracking-label uppercase leading-6">
              Adding...
            </span>
          </div>
        </div>
      )}

      {error && (
        <ErrorModal
          message={error}
          onDismiss={() => {
            setError(null);
            router.replace("/meal-plan");
          }}
        />
      )}
    </div>
  );
}
