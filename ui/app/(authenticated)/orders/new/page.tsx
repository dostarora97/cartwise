"use client";

import { Suspense, useState, useRef, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useRequiredAuth } from "@/lib/auth";
import { $api } from "@/lib/api/hooks";
import apiClient from "@/lib/api/client";
import { type ApiError, toApiError } from "@/lib/errors";
import { TopBar } from "@/components/top-bar";
import { ChipInput, type ChipInputHandle } from "@/components/chip-input";
import { Icon } from "@/components/icon";
import { ErrorBody } from "@/components/error-body";
import { BreadcrumbNav } from "@/components/breadcrumb-nav";
import { SwiggyOrderPicker } from "@/components/swiggy-order-picker";
import { InvoiceUpload } from "@/components/invoice-upload";

export default function InvoiceSetupPage() {
  return (
    <Suspense>
      <InvoiceSetupContent />
    </Suspense>
  );
}

function InvoiceSetupContent() {
  const { appUser } = useRequiredAuth();
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
  const [error, setError] = useState<ApiError | null>(null);

  const { data: users } = $api.useQuery("get", "/api/v1/users/");
  const otherUsers = (users ?? [])
    .filter((u) => u.id !== appUser.id)
    .map((u) => ({ id: u.id, name: u.name }));

  useEffect(() => {
    const p = searchParams.get("provider");
    const m = searchParams.get("method");
    if (p) setProvider(p);
    if (m) setMethod(m);

    if (searchParams.get("received") === "true") {
      setProvider("zomato");
      setMethod("invoice");
    }
  }, [searchParams]);

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
    if (!canSubmit) return;
    setSubmitting(true);
    setError(null);

    try {
      let sourceId: string;

      if (selectedOrderId) {
        const { data: source, error: sourceErr, response: sourceResp } = await apiClient.POST(
          "/api/v1/orders/sources/",
          { body: { type: "swiggy_order", raw_data: { swiggy_order_id: selectedOrderId } } },
        );
        if (sourceErr) {
          setError(toApiError("Failed to create source", sourceResp));
          return;
        }
        sourceId = source!.id;
      } else {
        const { data: upload, error: uploadErr, response: uploadResp } = await apiClient.POST(
          "/api/v1/orders/sources/upload",
          {
            body: { file: file! as unknown as string },
            bodySerializer() {
              const fd = new FormData();
              fd.append("file", file!);
              return fd;
            },
          },
        );
        if (uploadErr) {
          setError(toApiError("Failed to upload invoice", uploadResp));
          return;
        }
        sourceId = upload!.source_id;
      }

      const { data: order, error: orderErr, response: orderResp } = await apiClient.POST(
        "/api/v1/orders/",
        { body: { source_id: sourceId, participant_ids: [appUser.id, ...selectedOthers] } },
      );
      if (orderErr) {
        setError(toApiError("Failed to create order", orderResp));
        return;
      }
      router.push(`/orders/${order!.id}/expense`);
    } catch (e) {
      setError({ message: e instanceof Error ? e.message : "Unknown error" });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex flex-1 flex-col">
      <TopBar showBack onBack={() => router.push("/meal-plan")} />

      <div className="flex items-center gap-2 p-3 border-b border-black">
        <Icon name="currency_rupee" size={24} />
        <span className="text-2xl font-bold tracking-label uppercase leading-6">
          Expense
        </span>
      </div>

      <div className="flex items-stretch border-b border-gray-200">
        <div className="flex flex-wrap items-center gap-1 p-3 flex-1 text-base leading-6">
          <span>With <b>You</b>, &:</span>
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
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
          <div className="bg-white border border-black p-3 mx-3 max-w-sm w-full">
            <ErrorBody
              message={error.message}
              requestId={error.requestId}
              traceId={error.traceId}
              status={error.status}
              onRetry={() => {
                setError(null);
                handleSubmit();
              }}
            />
          </div>
        </div>
      )}
    </div>
  );
}
