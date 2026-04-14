"use client";

import { Suspense, useState, useRef, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { $api } from "@/lib/api/hooks";
import { TopBar } from "@/components/top-bar";
import { Chip } from "@/components/chip";
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

  const [file, setFile] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { data: users } = $api.useQuery("get", "/api/v1/users/");
  const otherUsers = users?.filter((u) => u.id !== appUser?.id) ?? [];

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
    if (!file || !session?.access_token || !users) return;
    setSubmitting(true);

    try {
      const participantIds = users.map((u) => u.id);
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

      <main className="flex-1 p-3 flex flex-col gap-6">
        {/* Participants */}
        <div className="flex flex-wrap items-center gap-2 text-base leading-6">
          <span>With <b>You</b>,</span>
          {otherUsers.map((u) => (
            <Chip key={u.id} label={u.name} />
          ))}
        </div>

        {/* File upload */}
        <label className="flex items-center gap-3 p-3 border border-gray-200 cursor-pointer">
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
      </main>

      {/* Bottom button */}
      <button
        onClick={handleAnalyse}
        disabled={!file || submitting}
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
