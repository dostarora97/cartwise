"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { useRequiredAuth } from "@/lib/auth";
import apiClient from "@/lib/api/client";
import { TopBar } from "@/components/top-bar";
import { MealPlanItem } from "@/components/meal-plan-item";
import { Icon } from "@/components/icon";
import { Spinner } from "@/components/spinner";

export default function ImportPage() {
  return (
    <Suspense>
      <ImportContent />
    </Suspense>
  );
}

type PreviewData = {
  name: string;
  items: { name: string }[];
  total: number;
};

type ImportState =
  | { status: "loading" }
  | { status: "preview"; data: PreviewData }
  | { status: "importing" }
  | { status: "done"; persist: number; skip: number }
  | { status: "error"; phase: "preview" | "import" };

function ImportContent() {
  useRequiredAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const token = searchParams.get("supplier");

  const [state, setState] = useState<ImportState>({ status: "loading" });

  const loadPreview = useCallback(async () => {
    if (!token) return;
    setState({ status: "loading" });
    try {
      const { data, error } = await apiClient.GET("/api/v1/imports/preview", {
        params: { query: { supplier: token } },
      });
      if (error) throw error;
      setState({ status: "preview", data: data as PreviewData });
    } catch {
      setState({ status: "error", phase: "preview" });
    }
  }, [token]);

  useEffect(() => {
    if (!token) {
      router.replace("/meal-plan");
      return;
    }
    loadPreview();
  }, [token, router, loadPreview]);

  async function handleImport() {
    if (!token) return;
    setState({ status: "importing" });
    try {
      const { data, error } = await apiClient.POST("/api/v1/imports/", {
        body: { supplier: token },
      });
      if (error) throw error;
      await queryClient.invalidateQueries({
        queryKey: ["get", "/api/v1/meal-plans"],
      });
      await queryClient.invalidateQueries({
        queryKey: ["get", "/api/v1/menu-items/"],
      });
      setState({
        status: "done",
        persist: data!.intents_applied.persist ?? 0,
        skip: data!.intents_applied.skip ?? 0,
      });
    } catch {
      setState({ status: "error", phase: "import" });
    }
  }

  return (
    <div className="flex flex-1 flex-col">
      <TopBar showBack onBack={() => router.push("/meal-plan")} />

      <div className="flex items-stretch justify-between border-b border-black">
        <span className="flex items-center p-3 text-2xl font-bold tracking-label uppercase leading-6">
          <Icon name="download" size={24} className="shrink-0 mr-3" />
          Import
        </span>
      </div>

      <main className={`flex flex-1 flex-col ${state.status === "loading" || state.status === "importing" || state.status === "error" || state.status === "done" ? "items-center justify-center" : ""}`}>
        {state.status === "loading" && <Spinner />}

        {state.status === "preview" && (
          <ul>
            {state.data.items.map((item, i) => (
              <MealPlanItem key={i} name={item.name} mode="view" />
            ))}
          </ul>
        )}

        {state.status === "importing" && <Spinner />}

        {state.status === "done" && (
          <div className="flex flex-col items-center gap-4">
            <p className="text-base font-bold tracking-label uppercase">
              Completed
            </p>
            <p className="text-sm tracking-wider">
              {state.persist} items added, {state.skip} skipped
            </p>
          </div>
        )}

        {state.status === "error" && (
          <div className="flex flex-col items-center gap-4">
            <p className="text-xs text-red-600 tracking-wider">
              {state.phase === "preview"
                ? "Could not load import preview"
                : "Import failed"}
            </p>
            <button
              onClick={state.phase === "preview" ? loadPreview : handleImport}
              className="border-2 border-black px-6 py-3 text-base font-bold tracking-label uppercase"
            >
              Retry
            </button>
          </div>
        )}
      </main>

      <div className="sticky bottom-0">
        {state.status === "preview" && (
          <button
            onClick={handleImport}
            disabled={state.data.total === 0}
            className="flex w-full items-center justify-center p-3 border-t border-black bg-black text-2xl font-bold tracking-label uppercase leading-6 text-white disabled:bg-neutral-400"
          >
            Import
          </button>
        )}
        {state.status === "done" && (
          <button
            onClick={() => router.push("/meal-plan")}
            className="flex w-full items-center justify-center p-3 border-t border-black bg-black text-2xl font-bold tracking-label uppercase leading-6 text-white"
          >
            OK
          </button>
        )}
      </div>
    </div>
  );
}
