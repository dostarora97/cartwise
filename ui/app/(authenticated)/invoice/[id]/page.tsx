"use client";

import { useState, useMemo } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/lib/auth";
import { $api } from "@/lib/api/hooks";
import apiClient from "@/lib/api/client";
import { TopBar } from "@/components/top-bar";
import { Icon } from "@/components/icon";
import { Chip } from "@/components/chip";
import { ChipInput } from "@/components/chip-input";
import { ErrorModal } from "@/components/error-modal";

// Typed shapes for the untyped JSON fields in OrderResponse
interface GroceryItem {
  upc: string;
  description: string;
  total: number;
}

interface SplitGroup {
  amount: number;
  groceryItems: GroceryItem[];
  splitEquallyAmong: string[];
}

interface OrderResult {
  paidBy: string;
  splits: SplitGroup[];
}

export default function SplitAnalysisPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const { appUser } = useAuth();

  const [mode, setMode] = useState<"view" | "edit">("view");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editError, setEditError] = useState("");
  const [editAssignments, setEditAssignments] = useState<Map<string, string[]>>(
    new Map(),
  );

  const { data: order, isLoading: orderLoading } = $api.useQuery(
    "get",
    "/api/v1/orders/{order_id}",
    { params: { path: { order_id: id } } },
  );

  const { data: users } = $api.useQuery("get", "/api/v1/users/");

  const userMap = useMemo(() => {
    const m = new Map<string, string>();
    users?.forEach((u) => m.set(u.id, u.name));
    return m;
  }, [users]);

  const result = order?.result as OrderResult | null;
  const participantUsers = useMemo(
    () =>
      (order?.participants ?? [])
        .map((p) => ({ id: p.user_id, name: userMap.get(p.user_id) ?? p.user_id }))
        .filter((u) => u.id !== appUser?.id)
        .concat(appUser ? [{ id: appUser.id, name: appUser.name }] : []),
    [order, userMap, appUser],
  );

  // All grocery items flattened (for edit mode)
  const allItems = useMemo(() => {
    if (!result) return [];
    const items: { item: GroceryItem; memberIds: string[] }[] = [];
    const seen = new Set<string>();
    for (const group of result.splits) {
      for (const gi of group.groceryItems) {
        if (!seen.has(gi.upc)) {
          seen.add(gi.upc);
          items.push({ item: gi, memberIds: [...group.splitEquallyAmong] });
        }
      }
    }
    return items;
  }, [result]);

  function enterEditMode() {
    const assignments = new Map<string, string[]>();
    for (const { item, memberIds } of allItems) {
      assignments.set(item.upc, [...memberIds]);
    }
    setEditAssignments(assignments);
    setEditError("");
    setMode("edit");
  }

  function resolveNames(memberIds: string[]) {
    return memberIds.map((id) => userMap.get(id) ?? id).join(", ");
  }

  async function handleBack() {
    if (mode === "edit") {
      setMode("view");
      return;
    }
    const confirmed = window.confirm(
      "Discard this split? The draft order will be cancelled.",
    );
    if (!confirmed) return;
    await apiClient.PATCH("/api/v1/orders/{order_id}/cancel", {
      params: { path: { order_id: id } },
    });
    router.replace("/meal-plan");
  }

  async function handleApprove() {
    setSubmitting(true);
    try {
      const { error: apiError } = await apiClient.POST(
        "/api/v1/orders/{order_id}/approve",
        { params: { path: { order_id: id } } },
      );
      if (apiError) throw new Error((apiError as { detail?: string }).detail || "Approve failed");
      router.push(`/invoice/${id}/result`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleConfirmEdits() {
    setSubmitting(true);
    setEditError("");
    try {
      const assignments = [...editAssignments.entries()].map(
        ([upc, member_ids]) => ({ upc, member_ids }),
      );
      const { error: apiError } = await apiClient.PUT(
        "/api/v1/orders/{order_id}/splits",
        {
          params: { path: { order_id: id } },
          body: { assignments },
        },
      );
      if (apiError) throw new Error((apiError as { detail?: string }).detail || "Edit failed");
      await queryClient.invalidateQueries({
        queryKey: ["get", "/api/v1/orders/{order_id}"],
      });
      setMode("view");
    } catch (e) {
      setEditError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setSubmitting(false);
    }
  }

  function updateAssignment(upc: string, memberIds: string[]) {
    setEditAssignments((prev) => {
      const next = new Map(prev);
      next.set(upc, memberIds);
      return next;
    });
  }

  if (orderLoading) return null;

  return (
    <div className="flex min-h-screen flex-col">
      <TopBar showBack onBack={handleBack} />

      {/* Status bar */}
      <div className="flex items-stretch justify-between border-b border-black">
        <span className="flex items-center p-3 text-2xl font-bold tracking-label uppercase leading-6">
          Split review
        </span>
        {mode === "view" && (
          <button
            onClick={enterEditMode}
            className="flex items-center justify-center p-3 bg-black"
          >
            <Icon name="edit" size={24} className="text-white" />
          </button>
        )}
      </div>

      {/* Content */}
      <main className="flex-1">
        {mode === "view" && result && (
          <div>
            {result.splits.map((group, gi) => (
              <div key={gi} className="border-b border-black last:border-b-0">
                <div className="p-3">
                  <span className="text-2xl font-bold tracking-label uppercase leading-6">
                    {resolveNames(group.splitEquallyAmong)}
                  </span>
                </div>
                {group.groceryItems.map((item) => (
                  <div
                    key={item.upc}
                    className="flex items-center p-3 border-t border-gray-200"
                  >
                    <span className="flex-1 text-base leading-6 truncate">
                      {item.description}
                    </span>
                  </div>
                ))}
              </div>
            ))}
          </div>
        )}

        {mode === "edit" && (
          <div>
            {allItems.map(({ item }) => (
              <div key={item.upc} className="border-b border-gray-200">
                <div className="p-3">
                  <span className="text-base font-medium leading-6">
                    {item.description}
                  </span>
                </div>
                <div className="px-3 pb-3">
                  <ChipInput
                    participants={participantUsers}
                    selected={editAssignments.get(item.upc) ?? []}
                    onAdd={(userId) => {
                      const current = editAssignments.get(item.upc) ?? [];
                      if (!current.includes(userId)) {
                        updateAssignment(item.upc, [...current, userId]);
                      }
                    }}
                    onRemove={(userId) => {
                      const current = editAssignments.get(item.upc) ?? [];
                      updateAssignment(
                        item.upc,
                        current.filter((id) => id !== userId),
                      );
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        )}
      </main>

      {/* Bottom button */}
      {mode === "view" && (
        <button
          onClick={handleApprove}
          disabled={submitting}
          className="sticky bottom-0 flex w-full items-center justify-center p-3 border-t border-black bg-black text-2xl font-bold tracking-label uppercase leading-6 text-white disabled:opacity-30"
        >
          {submitting ? "Splitting..." : "Split"}
        </button>
      )}

      {mode === "edit" && (
        <div className="sticky bottom-0">
          {editError && (
            <p className="p-3 text-xs text-red-600 tracking-wider bg-white border-t border-black">
              {editError}
            </p>
          )}
          <button
            onClick={handleConfirmEdits}
            disabled={submitting}
            className="flex w-full items-center justify-center p-3 border-t border-black bg-black text-2xl font-bold tracking-label uppercase leading-6 text-white disabled:opacity-30"
          >
            {submitting ? "Confirming..." : "Confirm"}
          </button>
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
