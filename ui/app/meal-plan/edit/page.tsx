"use client";

import { useState, useMemo, useRef } from "react";
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
  const originalPlanIds = useRef<Set<string>>(new Set());

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
    originalPlanIds.current = planIds;
    setInitialized(true);
  }

  // Sort once based on original plan membership, not current selection
  const sorted = useMemo(() => {
    if (!menuItems) return [];
    const items = [...menuItems];
    return items.sort((a, b) => {
      const aInPlan = originalPlanIds.current.has(a.id) ? 0 : 1;
      const bInPlan = originalPlanIds.current.has(b.id) ? 0 : 1;
      return aInPlan - bInPlan;
    });
  }, [menuItems]);

  const filtered = useMemo(() => {
    if (!search) return sorted;
    const q = search.toLowerCase();
    return sorted.filter(
      (i) =>
        i.name.toLowerCase().includes(q) || i.body.toLowerCase().includes(q),
    );
  }, [sorted, search]);

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
    sessionStorage.setItem(
      "meal-plan-selected",
      JSON.stringify(Array.from(selected)),
    );
    router.push("/meal-plan/reorder");
  }

  function checkboxColor(id: string) {
    if (!selected.has(id)) return "border-gray-400";
    if (originalPlanIds.current.has(id)) return "border-green-600 bg-green-600";
    return "border-gray-600 bg-gray-600";
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
          className="w-full border-b-2 border-black bg-transparent pb-2 text-sm font-medium tracking-item outline-none placeholder:text-gray-300 placeholder:uppercase"
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
                className={`h-5 w-5 shrink-0 appearance-none border-2 ${checkboxColor(item.id)}`}
              />
              <button
                onClick={() => router.push(`/menu-items/${item.id}`)}
                className="text-left text-sm font-medium tracking-item"
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
        className="fixed bottom-24 right-6 flex h-14 w-14 items-center justify-center border border-gray-800 bg-gray-800 text-white"
      >
        <Icon name="add" size={28} />
      </button>

      <div className="sticky bottom-0 border-t border-black bg-white px-6 py-4">
        <button
          onClick={handleOk}
          disabled={selected.size === 0}
          className="w-full bg-gray-800 py-4 text-sm font-bold tracking-label uppercase text-white disabled:opacity-30"
        >
          Save
        </button>
      </div>
    </div>
  );
}
