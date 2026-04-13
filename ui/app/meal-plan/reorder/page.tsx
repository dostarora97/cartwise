"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { $api } from "@/lib/api/hooks";
import apiClient from "@/lib/api/client";
import { TopBar } from "@/components/top-bar";
import { Icon } from "@/components/icon";

interface Item {
  id: string;
  name: string;
}

export default function MealPlanReorderPage() {
  const { appUser } = useAuth();
  const router = useRouter();
  const [items, setItems] = useState<Item[]>([]);
  const [saving, setSaving] = useState(false);
  const [dragIndex, setDragIndex] = useState<number | null>(null);

  const { data: menuItems } = $api.useQuery("get", "/api/v1/menu-items/", {
    params: { query: { status: "active" } },
  });

  useEffect(() => {
    const raw = sessionStorage.getItem("meal-plan-selected");
    if (!raw) {
      router.replace("/meal-plan/edit");
      return;
    }
    const ids: string[] = JSON.parse(raw);
    if (menuItems) {
      const lookup = new Map(menuItems.map((m) => [m.id, m.name]));
      setItems(ids.map((id) => ({ id, name: lookup.get(id) ?? id })));
    }
  }, [menuItems, router]);

  function handleDragStart(index: number) {
    setDragIndex(index);
  }

  function handleDragOver(e: React.DragEvent, index: number) {
    e.preventDefault();
    if (dragIndex === null || dragIndex === index) return;
    setItems((prev) => {
      const next = [...prev];
      const [moved] = next.splice(dragIndex, 1);
      next.splice(index, 0, moved);
      return next;
    });
    setDragIndex(index);
  }

  function handleDragEnd() {
    setDragIndex(null);
  }

  async function handleSave() {
    if (!appUser) return;
    setSaving(true);

    await apiClient.PUT("/api/v1/meal-plans/{user_id}", {
      params: { path: { user_id: appUser.id } },
      body: { menu_item_ids: items.map((i) => i.id) },
    });

    sessionStorage.removeItem("meal-plan-selected");
    router.replace("/");
  }

  return (
    <div className="flex min-h-screen flex-col">
      <TopBar showBack />

      <main className="flex-1 px-6 pt-6">
        <ul>
          {items.map((item, index) => (
            <li
              key={item.id}
              draggable
              onDragStart={() => handleDragStart(index)}
              onDragOver={(e) => handleDragOver(e, index)}
              onDragEnd={handleDragEnd}
              className={`flex items-center gap-4 border-b border-gray-200 py-5 cursor-grab active:cursor-grabbing ${
                dragIndex === index ? "opacity-50" : ""
              }`}
            >
              <Icon name="drag_indicator" size={20} className="text-gray-400" />
              <span className="text-sm font-medium tracking-item">
                {item.name}
              </span>
            </li>
          ))}
        </ul>
      </main>

      <div className="sticky bottom-0 border-t border-black bg-white px-6 py-4">
        <button
          onClick={handleSave}
          disabled={saving}
          className="w-full bg-gray-800 py-4 text-sm font-bold tracking-label uppercase text-white disabled:opacity-50"
        >
          {saving ? "Saving..." : "Save"}
        </button>
      </div>
    </div>
  );
}
