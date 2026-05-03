"use client";

import { useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import dynamic from "next/dynamic";
import { useRequiredAuth } from "@/lib/auth";
import { $api } from "@/lib/api/hooks";
import apiClient from "@/lib/api/client";
import { TopBar } from "@/components/top-bar";
import { MealPlanItem } from "@/components/meal-plan-item";
import { Icon } from "@/components/icon";
import { Spinner } from "@/components/spinner";

const MealPlanReorder = dynamic(() => import("@/components/meal-plan-reorder"));

type Mode = "select" | "reorder";

export default function MealPlanEditPage() {
  useRequiredAuth();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [mode, setMode] = useState<Mode>("select");
  const [search, setSearch] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const { data: menuItems, isLoading: menuItemsLoading } = $api.useQuery(
    "get",
    "/api/v1/menu-items/",
    { params: { query: { status: "active,archived" } } },
    { staleTime: 0 },
  );

  const { data: mealPlan, isLoading: mealPlanLoading } = $api.useQuery(
    "get",
    "/api/v1/meal-plans",
  );

  const initialIds = useMemo(() => {
    if (!mealPlan) return new Set<string>();
    return new Set(mealPlan.items.map((i) => i.menu_item.id));
  }, [mealPlan]);

  const [selected, setSelected] = useState<Set<string> | null>(null);
  const current = selected ?? initialIds;

  const isDirty = selected !== null;

  const [orderedItems, setOrderedItems] = useState<
    { id: string; name: string }[] | null
  >(null);

  const archivedIds = useMemo(() => {
    if (!menuItems) return new Set<string>();
    return new Set(menuItems.filter((i) => i.status === "archived").map((i) => i.id));
  }, [menuItems]);

  const sortedItems = useMemo(() => {
    if (!menuItems || !mealPlan) return [];

    const planRank = new Map(
      mealPlan.items.map((i) => [i.menu_item.id, i.rank]),
    );

    const inPlan: typeof menuItems = [];
    const activeNotInPlan: typeof menuItems = [];
    const archived: typeof menuItems = [];

    for (const item of menuItems) {
      if (planRank.has(item.id)) {
        inPlan.push(item);
      } else if (item.status === "active") {
        activeNotInPlan.push(item);
      } else {
        archived.push(item);
      }
    }

    inPlan.sort((a, b) => (planRank.get(a.id) ?? 0) - (planRank.get(b.id) ?? 0));
    activeNotInPlan.sort(
      (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime(),
    );
    archived.sort(
      (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime(),
    );

    return [...inPlan, ...activeNotInPlan, ...archived];
  }, [menuItems, mealPlan]);

  const filtered = useMemo(() => {
    if (!search) return sortedItems;
    const q = search.toLowerCase();
    return sortedItems.filter(
      (i) =>
        i.name.toLowerCase().includes(q) || i.body.toLowerCase().includes(q),
    );
  }, [sortedItems, search]);

  const dataReady = !menuItemsLoading && !mealPlanLoading && !!menuItems && !!mealPlan;

  function toggle(id: string) {
    const base = selected ?? initialIds;
    const next = new Set<string>(base);
    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }
    setSelected(next);
  }

  function handleNext() {
    if (!menuItems) return;
    const lookup = new Map(menuItems.map((m) => [m.id, m.name]));
    const items = Array.from(current).map((id) => ({
      id,
      name: lookup.get(id) ?? id,
    }));
    setOrderedItems(items);
    setMode("reorder");
  }

  async function handleSave() {
    if (!orderedItems) return;
    setSaving(true);
    setError("");

    const toUnarchive = orderedItems.filter((i) => archivedIds.has(i.id));
    for (const item of toUnarchive) {
      const { error: unarchiveError } = await apiClient.PATCH(
        "/api/v1/menu-items/{item_id}/unarchive",
        { params: { path: { item_id: item.id } } },
      );
      if (unarchiveError) {
        setError("Failed to unarchive items. Please try again.");
        setSaving(false);
        return;
      }
    }

    const { error: apiError } = await apiClient.PUT(
      "/api/v1/meal-plans",
      { body: { menu_item_ids: orderedItems.map((i) => i.id) } },
    );

    if (apiError) {
      setError("Failed to save. Please try again.");
      setSaving(false);
      return;
    }

    await queryClient.invalidateQueries({ queryKey: ["get", "/api/v1/meal-plans"] });
    await queryClient.invalidateQueries({ queryKey: ["get", "/api/v1/menu-items/"] });
    router.replace("/meal-plan");
  }

  return (
    <div className="flex flex-1 flex-col">
      <TopBar
        showBack
        onBack={mode === "reorder" ? () => setMode("select") : undefined}
      />

      <div className={`flex items-center border-b border-black ${mode === "select" ? "p-3" : ""}`}>
        {mode === "select" ? (
          <>
            <Icon name="search" size={24} className="shrink-0 mr-3" />
            <input
              id="search"
              name="search"
              type="text"
              autoComplete="off"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full h-6 bg-transparent text-2xl font-medium tracking-item leading-6 outline-none"
            />
          </>
        ) : (
          <span className="flex items-center text-2xl font-bold tracking-label uppercase leading-6">
            <span className="flex items-center justify-center p-3 shrink-0">
              <Icon name="check" size={24} />
            </span>
            <span>{orderedItems?.length ?? 0} item(s)</span>
          </span>
        )}
      </div>

      <main className={`flex flex-1 flex-col ${!dataReady ? "items-center justify-center" : ""}`}>
        {mode === "select" ? (
          dataReady ? (
            <>
              <ul>
                {filtered.map((item) => (
                  <MealPlanItem
                    key={item.id}
                    name={item.name}
                    mode="select"
                    checked={current.has(item.id)}
                    archived={archivedIds.has(item.id)}
                    onToggle={() => toggle(item.id)}
                    onTap={() => router.push(`/menu-items/${item.id}`)}
                  />
                ))}
              </ul>
              {filtered.length === 0 && (
                <p className="py-10 text-center text-sm tracking-wider text-neutral-400 uppercase">
                  No menu items found
                </p>
              )}
            </>
          ) : <Spinner />
        ) : (
          orderedItems && (
            <MealPlanReorder
              items={orderedItems}
              onReorder={setOrderedItems}
            />
          )
        )}
      </main>

      {mode === "select" && (
        <button
          onClick={() => router.push("/menu-items/new")}
          aria-label="New menu item"
          className="fixed bottom-24 right-12 flex h-14 w-14 items-center justify-center bg-black text-white shadow-[4px_4px_0_rgba(0,0,0,0.2)]"
        >
          <Icon name="add" size={24} />
        </button>
      )}

      <div className="sticky bottom-0">
        {error && (
          <p className="p-3 text-xs text-red-600 tracking-wider bg-white border-t border-black">{error}</p>
        )}
        {mode === "select" ? (
          isDirty && (
            <button
              onClick={handleNext}
              className="flex w-full items-center justify-center p-3 border-t border-black bg-black text-2xl font-bold tracking-label uppercase leading-6 text-white"
            >
              Next
            </button>
          )
        ) : (
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex w-full items-center justify-center p-3 border-t border-black bg-black text-2xl font-bold tracking-label uppercase leading-6 text-white disabled:bg-neutral-400"
          >
            {saving ? <div className="size-6 animate-spin rounded-full border-[3px] border-white border-t-transparent" /> : "Save"}
          </button>
        )}
      </div>
    </div>
  );
}
