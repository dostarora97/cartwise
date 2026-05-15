"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { useRequiredAuth } from "@/lib/auth";
import { $api } from "@/lib/api/hooks";
import apiClient from "@/lib/api/client";
import { TopBar } from "@/components/top-bar";
import { Icon } from "@/components/icon";
import { Spinner } from "@/components/spinner";

export default function ImportPage() {
  return (
    <Suspense>
      <ImportContent />
    </Suspense>
  );
}

type ImportState =
  | { status: "idle" }
  | { status: "importing"; supplierId: string }
  | { status: "done"; persist: number; skip: number }
  | { status: "error"; message: string; supplierId: string };

function ImportContent() {
  useRequiredAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const supplierParam = searchParams.get("supplier");

  const [state, setState] = useState<ImportState>({ status: "idle" });

  const { data: suppliers, isLoading } = $api.useQuery(
    "get",
    "/api/v1/imports/suppliers",
  );

  const filtered = supplierParam
    ? suppliers?.filter((s) => s.id === supplierParam)
    : undefined;
  const displaySuppliers =
    filtered && filtered.length > 0 ? filtered : suppliers;

  async function handleImport(supplierId: string) {
    setState({ status: "importing", supplierId });
    try {
      const { data, error } = await apiClient.POST("/api/v1/imports/", {
        body: { supplier_id: supplierId },
      });
      if (error) {
        throw new Error(
          (error as { detail?: string }).detail || "Import failed",
        );
      }
      await queryClient.invalidateQueries({
        queryKey: ["get", "/api/v1/meal-plans"],
      });
      await queryClient.invalidateQueries({
        queryKey: ["get", "/api/v1/menu-items/"],
      });
      setState({
        status: "done",
        persist: data.intents_applied.persist ?? 0,
        skip: data.intents_applied.skip ?? 0,
      });
    } catch (e) {
      setState({
        status: "error",
        message: e instanceof Error ? e.message : "Unknown error",
        supplierId,
      });
    }
  }

  const ready = !isLoading;

  return (
    <div className="flex flex-1 flex-col">
      <TopBar showBack onBack={() => router.push("/meal-plan")} />

      <div className="flex items-stretch justify-between border-b border-black">
        <span className="flex items-center p-3 text-2xl font-bold tracking-label uppercase leading-6">
          <Icon name="download" size={24} />
          <span className="ml-2">Import</span>
        </span>
      </div>

      <main className="flex flex-1 flex-col p-3">
        {!ready && (
          <div className="flex flex-1 items-center justify-center">
            <Spinner />
          </div>
        )}

        {state.status === "done" && (
          <div className="flex flex-1 flex-col items-center justify-center gap-4">
            <p className="text-base font-bold tracking-label uppercase">
              Import complete
            </p>
            <p className="text-xs tracking-wider">
              {state.persist} items added, {state.skip} skipped
            </p>
            <button
              onClick={() => router.push("/meal-plan")}
              className="flex items-center gap-2 bg-black text-white p-3 text-base font-bold tracking-label uppercase h-12"
            >
              OK
            </button>
          </div>
        )}

        {state.status === "error" && (
          <div className="flex flex-1 flex-col items-center justify-center gap-4">
            <p className="text-xs text-red-600 tracking-wider">
              {state.message}
            </p>
            <button
              onClick={() => handleImport(state.supplierId)}
              className="border-2 border-black px-6 py-3 text-base font-bold tracking-label uppercase"
            >
              Retry
            </button>
          </div>
        )}

        {ready && (state.status === "idle" || state.status === "importing") && (
          <ul className="flex flex-col gap-3">
            {displaySuppliers?.map((supplier) => (
              <li
                key={supplier.id}
                className="flex items-center justify-between border border-black p-3 h-12"
              >
                <span className="text-base font-bold tracking-label uppercase">
                  {supplier.name}
                </span>
                <button
                  onClick={() => handleImport(supplier.id)}
                  disabled={state.status === "importing"}
                  className="flex items-center gap-1 bg-black text-white px-3 py-1 text-sm font-bold tracking-label uppercase disabled:bg-neutral-400"
                >
                  {state.status === "importing" &&
                  state.supplierId === supplier.id ? (
                    <div className="size-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                  ) : (
                    "Import"
                  )}
                </button>
              </li>
            ))}
          </ul>
        )}
      </main>
    </div>
  );
}
