"use client";

import { useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { $api } from "@/lib/api/hooks";
import apiClient from "@/lib/api/client";
import { TopBar } from "@/components/top-bar";
import { MealPlanItem } from "@/components/meal-plan-item";
import { Icon } from "@/components/icon";

type Mode = "select" | "reorder";

export default function MealPlanEditPage() {
  const { appUser } = useAuth();
  const router = useRouter();
  const [mode, setMode] = useState<Mode>("select");
  const [search, setSearch] = useState("");
  const [saving, setSaving] = useState(false);
  const [dragIndex, setDragIndex] = useState<number | null>(null);

  const { data: menuItems } = $api.useQuery("get", "/api/v1/menu-items/", {
    params: { query: { status: "active", created_by: appUser!.id } },
  });

  const { data: mealPlan } = $api.useQuery(
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

  function handleDragOver(e: React.DragEvent, index: number) {
    e.preventDefault();
    if (dragIndex === null || dragIndex === index) return;
    setOrderedItems((prev) => {
      if (!prev) return prev;
      const next = [...prev];
      const [moved] = next.splice(dragIndex, 1);
      next.splice(index, 0, moved);
      return next;
    });
    setDragIndex(index);
  }

  async function handleSave() {
    if (!orderedItems) return;
    setSaving(true);
    await apiClient.PUT("/api/v1/meal-plans/{user_id}", {
      params: { path: { user_id: appUser!.id } },
      body: { menu_item_ids: orderedItems.map((i) => i.id) },
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
        ) : (
          <ul>
            {orderedItems?.map((item, index) => (
              <MealPlanItem
                key={item.id}
                name={item.name}
                mode="reorder"
                dragging={dragIndex === index}
                onDragStart={() => setDragIndex(index)}
                onDragOver={(e) => handleDragOver(e, index)}
                onDragEnd={() => setDragIndex(null)}
              />
            ))}
          </ul>
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
