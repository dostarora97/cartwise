"use client";

import { useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { $api } from "@/lib/api/hooks";
import { TopBar } from "@/components/top-bar";
import { Icon } from "@/components/icon";

export default function MealPlanEditPage() {
  const { appUser } = useAuth();
  const router = useRouter();
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [initialized, setInitialized] = useState(false);

  const { data: menuItems } = $api.useQuery(
    "get",
    "/api/v1/menu-items/",
    { params: { query: { status: "active", created_by: appUser?.id ?? "" } } },
    { enabled: !!appUser },
  );

  const { data: mealPlan } = $api.useQuery(
    "get",
    "/api/v1/meal-plans/{user_id}",
    { params: { path: { user_id: appUser?.id ?? "" } } },
    { enabled: !!appUser },
  );

  // Initialize selected from current meal plan (once)
  if (mealPlan && !initialized) {
    const planIds = new Set(mealPlan.items.map((i) => i.menu_item.id));
    setSelected(planIds);
    setInitialized(true);
  }

  const filtered = useMemo(() => {
    if (!menuItems) return [];
    const items = [...menuItems];
    if (search) {
      const q = search.toLowerCase();
      return items.filter(
        (i) =>
          i.name.toLowerCase().includes(q) ||
          i.body.toLowerCase().includes(q),
      );
    }
    // Default sort: selected first
    return items.sort((a, b) => {
      const aSelected = selected.has(a.id) ? 0 : 1;
      const bSelected = selected.has(b.id) ? 0 : 1;
      return aSelected - bSelected;
    });
  }, [menuItems, search, selected]);

  function toggle(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }

  function handleOk() {
    // Pass selected IDs to reorder page via sessionStorage
    sessionStorage.setItem(
      "meal-plan-selected",
      JSON.stringify(Array.from(selected)),
    );
    router.push("/meal-plan/reorder");
  }

  return (
    <div className="flex min-h-screen flex-col">
      <TopBar showBack />

      <div className="px-6 pt-6 pb-4">
        <input
          type="text"
          placeholder="SEARCH ITEMS..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full border-b-2 border-black bg-transparent pb-2 text-sm font-medium tracking-[0.15em] uppercase outline-none placeholder:text-gray-300"
        />
      </div>

      <main className="flex-1 px-6">
        <ul>
          {filtered.map((item) => (
            <li key={item.id} className="flex items-center gap-4 py-4">
              <input
                type="checkbox"
                checked={selected.has(item.id)}
                onChange={() => toggle(item.id)}
                className="h-5 w-5 shrink-0 appearance-none border-2 border-black checked:bg-black checked:border-black"
              />
              <button
                onClick={() => router.push(`/menu-items/${item.id}`)}
                className="text-left text-sm font-medium tracking-[0.15em] uppercase"
              >
                {item.name}
              </button>
            </li>
          ))}
        </ul>

        {filtered.length === 0 && (
          <p className="py-10 text-center text-sm tracking-wider text-gray-400 uppercase">
            No menu items found
          </p>
        )}
      </main>

      <button
        onClick={() => router.push("/menu-items/new")}
        className="fixed bottom-24 right-6 flex h-14 w-14 items-center justify-center rounded-full bg-black text-white shadow-lg"
      >
        <Icon name="add" size={28} />
      </button>

      <div className="sticky bottom-0 border-t border-black bg-white px-6 py-4">
        <button
          onClick={handleOk}
          disabled={selected.size === 0}
          className="w-full bg-black py-4 text-sm font-bold tracking-[0.2em] uppercase text-white disabled:opacity-30"
        >
          Save
        </button>
      </div>
    </div>
  );
}
