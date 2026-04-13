"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import Markdown from "react-markdown";
import { useAuth } from "@/lib/auth";
import { $api } from "@/lib/api/hooks";
import apiClient from "@/lib/api/client";
import { Icon } from "@/components/icon";

interface MenuItemPageProps {
  itemId?: string; // undefined = new item
}

export function MenuItemPage({ itemId }: MenuItemPageProps) {
  const { appUser } = useAuth();
  const router = useRouter();
  const queryClient = useQueryClient();
  const isNew = !itemId;

  // Mode
  const [editing, setEditing] = useState(isNew);

  // Form state
  const [name, setName] = useState("");
  const [body, setBody] = useState("");
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);

  // FAB state
  const [fabOpen, setFabOpen] = useState(false);
  const [fabLoading, setFabLoading] = useState(false);

  // TopBar scroll collapse
  const headerRef = useRef<HTMLDivElement>(null);
  const sentinelRef = useRef<HTMLDivElement>(null);
  const [collapsed, setCollapsed] = useState(false);

  // Fetch item data (skip for new)
  const { data: item } = $api.useQuery(
    "get",
    "/api/v1/menu-items/{item_id}",
    { params: { path: { item_id: itemId ?? "" } } },
    { enabled: !!itemId },
  );

  // Fetch meal plan to check if item is in plan
  const { data: mealPlan } = $api.useQuery(
    "get",
    "/api/v1/meal-plans/{user_id}",
    { params: { path: { user_id: appUser!.id } } },
  );

  const inPlan = mealPlan?.items.some((i) => i.menu_item.id === itemId) ?? false;
  const isArchived = item?.status === "archived";

  // Initialize form from fetched data
  useEffect(() => {
    if (item && !dirty) {
      setName(item.name);
      setBody(item.body);
    }
  }, [item, dirty]);

  // Native beforeunload warning for unsaved changes
  useEffect(() => {
    if (!dirty) return;
    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault();
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [dirty]);

  // TopBar scroll collapse via IntersectionObserver
  useEffect(() => {
    const sentinel = sentinelRef.current;
    if (!sentinel) return;
    const observer = new IntersectionObserver(
      ([entry]) => setCollapsed(!entry.isIntersecting),
      { threshold: 0 },
    );
    observer.observe(sentinel);
    return () => observer.disconnect();
  }, []);

  function handleEdit() {
    setEditing(true);
  }

  function handleFormChange(field: "name" | "body", value: string) {
    if (field === "name") setName(value);
    else setBody(value);
    setDirty(true);
  }

  async function handleSave() {
    setSaving(true);

    if (isNew) {
      const { error } = await apiClient.POST("/api/v1/menu-items/", {
        body: { name, body },
      });
      if (error) {
        setSaving(false);
        return;
      }
      await queryClient.invalidateQueries({
        queryKey: ["get", "/api/v1/menu-items/"],
      });
      router.replace("/meal-plan/edit");
    } else {
      const { error } = await apiClient.PATCH(
        "/api/v1/menu-items/{item_id}",
        {
          params: { path: { item_id: itemId! } },
          body: { name, body },
        },
      );
      if (error) {
        setSaving(false);
        return;
      }
      await queryClient.invalidateQueries({
        queryKey: ["get", "/api/v1/menu-items/{item_id}"],
      });
      setDirty(false);
      setSaving(false);
      setEditing(false);
    }
  }

  const handleFabAction = useCallback(
    async (action: "togglePlan" | "toggleArchive") => {
      setFabOpen(false);
      setFabLoading(true);

      if (action === "togglePlan") {
        if (inPlan) {
          await apiClient.DELETE(
            "/api/v1/meal-plans/{user_id}/items/{menu_item_id}",
            {
              params: {
                path: {
                  user_id: appUser!.id,
                  menu_item_id: itemId!,
                },
              },
            },
          );
        } else {
          await apiClient.POST("/api/v1/meal-plans/{user_id}/items", {
            params: { path: { user_id: appUser!.id } },
            body: { menu_item_id: itemId! },
          });
        }
        await queryClient.invalidateQueries({
          queryKey: ["get", "/api/v1/meal-plans/{user_id}"],
        });
      } else {
        if (isArchived) {
          await apiClient.PATCH(
            "/api/v1/menu-items/{item_id}/unarchive",
            { params: { path: { item_id: itemId! } } },
          );
        } else {
          await apiClient.PATCH("/api/v1/menu-items/{item_id}/archive", {
            params: { path: { item_id: itemId! } },
          });
        }
        await queryClient.invalidateQueries({
          queryKey: ["get", "/api/v1/menu-items/{item_id}"],
        });
        await queryClient.invalidateQueries({
          queryKey: ["get", "/api/v1/meal-plans/{user_id}"],
        });
      }

      setFabLoading(false);
    },
    [appUser, itemId, inPlan, isArchived, queryClient],
  );

  function handleBack() {
    if (editing && dirty) {
      // Native form warning handled by beforeunload
      // For in-app navigation, check dirty state
      const confirmed = window.confirm(
        "You have unsaved changes. Discard?",
      );
      if (!confirmed) return;
    }
    router.back();
  }

  return (
    <div className="flex min-h-screen flex-col">
      {/* Sentinel for scroll detection */}
      <div ref={sentinelRef} className="h-0" />

      {/* TopBar with collapsible title */}
      <header
        ref={headerRef}
        className="sticky top-0 z-50 border-b border-black bg-white px-4 transition-all"
      >
        <div className="flex items-center gap-2 h-14">
          <button onClick={handleBack} className="flex shrink-0">
            <Icon name="chevron_left" size={24} />
          </button>
          <span
            className={`flex-1 text-sm font-bold tracking-heading uppercase transition-all ${
              collapsed ? "truncate" : "break-words"
            }`}
          >
            {isNew ? "NEW ITEM" : name || "CARTWISE"}
          </span>
        </div>
      </header>

      {/* Content */}
      <main className="flex-1 px-6 py-6">
        {editing ? (
          <div className="flex flex-col gap-6">
            <div>
              <label className="text-xs font-bold tracking-label uppercase">
                Name
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => handleFormChange("name", e.target.value)}
                placeholder="Item name"
                className="mt-2 block w-full border-b-2 border-black bg-transparent pb-2 text-base font-medium tracking-wider outline-none placeholder:text-gray-300"
              />
            </div>
            <div>
              <label className="text-xs font-bold tracking-label uppercase">
                Body
              </label>
              <textarea
                value={body}
                onChange={(e) => handleFormChange("body", e.target.value)}
                placeholder="Write markdown here..."
                rows={15}
                className="mt-2 block w-full resize-none border-b-2 border-black bg-transparent pb-2 text-sm font-medium leading-relaxed outline-none placeholder:text-gray-300"
              />
            </div>
          </div>
        ) : (
          <div
            onClick={handleEdit}
            className="cursor-pointer active:underline active:decoration-dotted"
          >
            <article className="prose prose-sm max-w-none font-mono">
              <Markdown>{body || "*No content yet*"}</Markdown>
            </article>
          </div>
        )}
      </main>

      {/* Bottom bar — only in edit mode */}
      {editing && (
        <div className="sticky bottom-0 border-t border-black bg-white px-6 py-4">
          <button
            onClick={handleSave}
            disabled={saving || !name.trim()}
            className="w-full bg-neutral-800 py-4 text-sm font-bold tracking-label uppercase text-white disabled:opacity-30"
          >
            {saving ? "Saving..." : "Save"}
          </button>
        </div>
      )}

      {/* FAB — only in view mode for existing items */}
      {!editing && !isNew && (
        <div className="fixed bottom-6 right-6 z-40">
          {fabOpen ? (
            <div className="flex flex-col gap-3 border border-neutral-800 bg-white p-4 shadow-lg">
              <label className="flex items-center gap-3 text-xs font-bold tracking-label uppercase cursor-pointer">
                <input
                  type="checkbox"
                  checked={inPlan}
                  onChange={() => handleFabAction("togglePlan")}
                  className="h-4 w-4 appearance-none border-2 border-neutral-400 checked:border-neutral-800 checked:bg-neutral-800 checked:shadow-[inset_0_0_0_2px_white]"
                />
                In meal plan
              </label>
              <label className="flex items-center gap-3 text-xs font-bold tracking-label uppercase cursor-pointer">
                <input
                  type="checkbox"
                  checked={isArchived}
                  onChange={() => handleFabAction("toggleArchive")}
                  className="h-4 w-4 appearance-none border-2 border-neutral-400 checked:border-neutral-800 checked:bg-neutral-800 checked:shadow-[inset_0_0_0_2px_white]"
                />
                Archived
              </label>
            </div>
          ) : (
            <button
              onClick={() => (fabLoading ? null : setFabOpen(true))}
              className="flex h-14 w-14 items-center justify-center border border-neutral-800 bg-neutral-800 text-white"
            >
              {fabLoading ? (
                <div className="h-5 w-5 animate-spin rounded-full border-2 border-white border-t-transparent" />
              ) : (
                <Icon name="more_horiz" size={24} />
              )}
            </button>
          )}
        </div>
      )}

      {/* Click outside to close FAB */}
      {fabOpen && (
        <div
          className="fixed inset-0 z-30"
          onClick={() => setFabOpen(false)}
        />
      )}
    </div>
  );
}
