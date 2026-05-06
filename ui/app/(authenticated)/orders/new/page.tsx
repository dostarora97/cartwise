"use client";

import { Suspense, useState, useRef, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useRequiredAuth } from "@/lib/auth";
import { $api } from "@/lib/api/hooks";
import { TopBar } from "@/components/top-bar";
import { ChipInput, type ChipInputHandle } from "@/components/chip-input";
import { Icon } from "@/components/icon";
import { ErrorModal } from "@/components/error-modal";
import { BreadcrumbNav } from "@/components/breadcrumb-nav";
import { SwiggyOrderPicker } from "@/components/swiggy-order-picker";
import { InvoiceUpload } from "@/components/invoice-upload";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function InvoiceSetupPage() {
  return (
    <Suspense>
      <InvoiceSetupContent />
    </Suspense>
  );
}

function InvoiceSetupContent() {
  const { appUser, session } = useRequiredAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const chipInputRef = useRef<ChipInputHandle>(null);

  const [provider, setProvider] = useState<string | null>(null);
  const [method, setMethod] = useState<string | null>(null);
  const [selectedOrderId, setSelectedOrderId] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [selectedOthers, setSelectedOthers] = useState<string[]>([]);
  const [showingAll, setShowingAll] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { data: users } = $api.useQuery("get", "/api/v1/users/");
  const otherUsers = (users ?? [])
    .filter((u) => u.id !== appUser.id)
    .map((u) => ({ id: u.id, name: u.name }));

  // Restore state from query params (OAuth return or Web Share Target)
  useEffect(() => {
    const p = searchParams.get("provider");
    const m = searchParams.get("method");
    if (p) setProvider(p);
    if (m) setMethod(m);

    // Web Share Target: auto-select Zomato > Invoice
    if (searchParams.get("received") === "true") {
      setProvider("zomato");
      setMethod("invoice");
    }
  }, [searchParams]);

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

  const canSubmit =
    selectedOthers.length > 0 && (selectedOrderId || file);

  async function handleSubmit() {
    if (!canSubmit || !session?.access_token) return;
    setSubmitting(true);

    try {
      if (selectedOrderId) {
        // Swiggy order flow: create source → create order
        const sourceResp = await fetch(`${API_BASE}/api/v1/orders/sources/`, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${session.access_token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            type: "swiggy_order",
            raw_data: { swiggy_order_id: selectedOrderId },
          }),
        });

        if (!sourceResp.ok) {
          const body = await sourceResp.json().catch(() => ({ detail: "Unknown error" }));
          throw new Error(body.detail || `HTTP ${sourceResp.status}`);
        }

        const source = await sourceResp.json();
        const participantIds = [appUser.id, ...selectedOthers];

        const orderResp = await fetch(`${API_BASE}/api/v1/orders/`, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${session.access_token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            source_id: source.id,
            participant_ids: participantIds,
          }),
        });

        if (!orderResp.ok) {
          const body = await orderResp.json().catch(() => ({ detail: "Unknown error" }));
          throw new Error(body.detail || `HTTP ${orderResp.status}`);
        }

        const order = await orderResp.json();
        router.push(`/orders/${order.id}/expense`);
      } else if (file) {
        // Invoice flow: upload file → create order
        const formData = new FormData();
        formData.append("file", file);

        const uploadResp = await fetch(`${API_BASE}/api/v1/orders/sources/upload`, {
          method: "POST",
          headers: { Authorization: `Bearer ${session.access_token}` },
          body: formData,
        });

        if (!uploadResp.ok) {
          const body = await uploadResp.json().catch(() => ({ detail: "Unknown error" }));
          throw new Error(body.detail || `HTTP ${uploadResp.status}`);
        }

        const source = await uploadResp.json();
        const participantIds = [appUser.id, ...selectedOthers];

        const orderResp = await fetch(`${API_BASE}/api/v1/orders/`, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${session.access_token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            source_id: source.source_id,
            participant_ids: participantIds,
          }),
        });

        if (!orderResp.ok) {
          const body = await orderResp.json().catch(() => ({ detail: "Unknown error" }));
          throw new Error(body.detail || `HTTP ${orderResp.status}`);
        }

        const order = await orderResp.json();
        router.push(`/orders/${order.id}/expense`);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex flex-1 flex-col">
      <TopBar showBack onBack={() => router.push("/meal-plan")} />

      {/* Expense heading */}
      <div className="flex items-center p-3 border-b border-black">
        <span className="text-2xl font-bold tracking-label uppercase leading-6">
          Expense
        </span>
      </div>

      {/* Participants */}
      <div className="flex items-stretch border-b border-gray-200">
        <div className="flex flex-wrap items-center gap-1 p-3 flex-1 text-base leading-6">
          <span>With <b>You</b>, and:</span>
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

      {/* Breadcrumb navigation */}
      <BreadcrumbNav
        provider={provider}
        method={method}
        onProviderChange={(p) => {
          setProvider(p);
          setMethod(null);
          setSelectedOrderId(null);
          setFile(null);
        }}
        onMethodChange={(m) => {
          setMethod(m);
          setSelectedOrderId(null);
          setFile(null);
        }}
      />

      {/* Method-specific UI */}
      <main className="flex-1">
        {method === "order" && (
          <SwiggyOrderPicker
            selectedOrderId={selectedOrderId}
            onSelect={setSelectedOrderId}
          />
        )}
        {method === "invoice" && (
          <InvoiceUpload file={file} onFileChange={setFile} />
        )}
      </main>

      {/* Bottom button */}
      {canSubmit && (
        <button
          onClick={handleSubmit}
          disabled={submitting}
          className="sticky bottom-0 flex w-full items-center justify-center p-3 border-t border-black bg-black text-2xl font-bold tracking-label uppercase leading-6 text-white disabled:bg-neutral-400"
        >
          {submitting ? <div className="size-6 animate-spin rounded-full border-[3px] border-white border-t-transparent" /> : "Add"}
        </button>
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
