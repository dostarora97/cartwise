"use client";

import { useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import dynamic from "next/dynamic";
import { useAuth } from "@/lib/auth";
import { $api } from "@/lib/api/hooks";
import apiClient from "@/lib/api/client";
import { TopBar } from "@/components/top-bar";
import { MealPlanItem } from "@/components/meal-plan-item";
import { Icon } from "@/components/icon";

const MealPlanReorder = dynamic(() => import("@/components/meal-plan-reorder"));

type Mode = "select" | "reorder";

export default function MealPlanEditPage() {
  const { appUser } = useAuth();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [mode, setMode] = useState<Mode>("select");
  const [search, setSearch] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const { data: menuItems, isLoading: menuItemsLoading } = $api.useQuery(
    "get",
    "/api/v1/menu-items/",
    { params: { query: { status: "active", created_by: appUser!.id } } },
  );

  const { data: mealPlan, isLoading: mealPlanLoading } = $api.useQuery(
    "get",
    "/api/v1/meal-plans/{user_id}",
    { params: { path: { user_id: appUser!.id } } },
  );

  const initialIds = useMemo(() => {
    if (!mealPlan) return new Set<string>();
    return new Set(mealPlan.items.map((i) => i.menu_item.id));
  }, [mealPlan]);

  const [selected, setSelected] = useState<Set<string> | null>(null);
  const current = selected ?? initialIds;

  const [orderedItems, setOrderedItems] = useState<
    { id: string; name: string }[] | null
  >(null);

  const filtered = useMemo(() => {
    if (!menuItems) return [];
    const items = [...menuItems].sort((a, b) => a.name.localeCompare(b.name));
    if (!search) return items;
    const q = search.toLowerCase();
    return items.filter(
      (i) =>
        i.name.toLowerCase().includes(q) || i.body.toLowerCase().includes(q),
    );
  }, [menuItems, search]);

  const dataReady = !menuItemsLoading && !mealPlanLoading;

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

    const { error: apiError } = await apiClient.PUT(
      "/api/v1/meal-plans/{user_id}",
      {
        params: { path: { user_id: appUser!.id } },
        body: { menu_item_ids: orderedItems.map((i) => i.id) },
      },
    );

    if (apiError) {
      setError("Failed to save. Please try again.");
      setSaving(false);
      return;
    }

    await queryClient.invalidateQueries({
      queryKey: ["get", "/api/v1/meal-plans/{user_id}"],
    });
    router.replace("/meal-plan");
  }

  return (
    <div className="flex min-h-screen flex-col">
      <TopBar
        showBack
        onBack={mode === "reorder" ? () => setMode("select") : undefined}
      />

      <div className="flex items-center p-3 border-b border-black">
        {mode === "select" ? (
          <input
            id="search"
            name="search"
            type="text"
            autoComplete="off"
            placeholder="SEARCH ITEMS..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full h-6 bg-transparent text-2xl font-medium tracking-item leading-6 outline-none placeholder:text-gray-300 placeholder:uppercase"
          />
        ) : (
          <span className="text-2xl font-bold tracking-label uppercase leading-6">
            {orderedItems?.length ?? 0} items selected
          </span>
        )}
      </div>

      <main className="flex-1">
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
          ) : null
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
          className="fixed bottom-24 right-12 flex h-14 w-14 items-center justify-center bg-black text-white"
        >
          <Icon name="add" size={24} />
        </button>
      )}

      <div className="sticky bottom-0">
        {error && (
          <p className="p-3 text-xs text-red-600 tracking-wider bg-white border-t border-black">{error}</p>
        )}
        {mode === "select" ? (
          <button
            onClick={handleNext}
            disabled={current.size === 0}
            className="flex w-full items-center justify-center p-3 border-t border-black bg-black text-2xl font-bold tracking-label uppercase leading-6 text-white disabled:opacity-30"
          >
            Next
          </button>
        ) : (
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex w-full items-center justify-center p-3 border-t border-black bg-black text-2xl font-bold tracking-label uppercase leading-6 text-white disabled:opacity-50"
          >
            {saving ? "Saving..." : "Save"}
          </button>
        )}
      </div>
    </div>
  );
}
