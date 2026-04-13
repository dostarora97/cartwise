"use client";

import { useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { DragDropProvider } from "@dnd-kit/react";
import { useSortable } from "@dnd-kit/react/sortable";
import { move } from "@dnd-kit/helpers";
import { useAuth } from "@/lib/auth";
import { $api } from "@/lib/api/hooks";
import apiClient from "@/lib/api/client";
import { TopBar } from "@/components/top-bar";
import { MealPlanItem } from "@/components/meal-plan-item";
import { Icon } from "@/components/icon";

type Mode = "select" | "reorder";

function SortableItem({
  id,
  name,
  index,
}: {
  id: string;
  name: string;
  index: number;
}) {
  const { ref, handleRef, isDragging } = useSortable({ id, index });

  return (
    <li
      ref={ref}
      className={`flex items-center gap-4 border-b border-gray-200 py-5 last:border-b-0 ${
        isDragging ? "opacity-50" : ""
      }`}
    >
      <div className="w-6 shrink-0 flex justify-center">
        <button
          ref={handleRef}
          type="button"
          aria-label="Drag to reorder"
          className="touch-none cursor-grab active:cursor-grabbing"
        >
          <Icon name="drag_indicator" size={20} className="text-neutral-400" />
        </button>
      </div>
      <span className="flex-1 text-sm font-medium tracking-item">{name}</span>
    </li>
  );
}

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

  // TODO: Add selected-first sort (relevance). Currently alphabetical only.

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

      <div className="border-b border-black px-6 py-4">
        {mode === "select" ? (
          <input
            type="text"
            placeholder="SEARCH ITEMS..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-transparent text-sm font-medium tracking-item outline-none placeholder:text-gray-300 placeholder:uppercase"
          />
        ) : (
          <span className="text-sm font-bold tracking-label uppercase">
            {orderedItems?.length ?? 0} items selected
          </span>
        )}
      </div>

      <main className="flex-1 px-6">
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
            <DragDropProvider
              onDragEnd={(event) => {
                if (event.canceled) return;
                setOrderedItems((items) =>
                  items ? move(items, event) : items,
                );
              }}
            >
              <ul>
                {orderedItems.map((item, index) => (
                  <SortableItem
                    key={item.id}
                    id={item.id}
                    name={item.name}
                    index={index}
                  />
                ))}
              </ul>
            </DragDropProvider>
          )
        )}
      </main>

      {mode === "select" && (
        <button
          onClick={() => router.push("/menu-items/new")}
          className="fixed bottom-24 right-6 flex h-14 w-14 items-center justify-center border border-neutral-800 bg-neutral-800 text-white"
        >
          <Icon name="add" size={28} />
        </button>
      )}

      <div className="sticky bottom-0 border-t border-black bg-white px-6 py-4">
        {error && (
          <p className="mb-2 text-xs text-red-600 tracking-wider">{error}</p>
        )}
        {mode === "select" ? (
          <button
            onClick={handleNext}
            disabled={current.size === 0}
            className="w-full bg-neutral-800 py-4 text-sm font-bold tracking-label uppercase text-white disabled:opacity-30"
          >
            Next
          </button>
        ) : (
          <button
            onClick={handleSave}
            disabled={saving}
            className="w-full bg-neutral-800 py-4 text-sm font-bold tracking-label uppercase text-white disabled:opacity-50"
          >
            {saving ? "Saving..." : "Save"}
          </button>
        )}
      </div>
    </div>
  );
}
