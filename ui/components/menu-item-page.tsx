"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import Markdown from "react-markdown";
import { useAuth } from "@/lib/auth";
import { $api } from "@/lib/api/hooks";
import apiClient from "@/lib/api/client";
import { TopBar } from "@/components/top-bar";
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

  // More popup state
  const [moreOpen, setMoreOpen] = useState(false);
  const [moreLoading, setMoreLoading] = useState(false);
  const moreRef = useRef<HTMLButtonElement>(null);
  const nameRef = useRef<HTMLHeadingElement>(null);

  // Sticky heading scroll state
  const sentinelRef = useRef<HTMLDivElement>(null);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const stickyBarRef = useRef<HTMLDivElement>(null);

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

  // Collapse heading when the TopBar scrolls above the viewport.
  // We mutate the DOM directly (not React state) to avoid an infinite
  // layout-thrashing loop: setState → re-render → height change → scroll
  // event → setState → …
  //
  // The heading shrinking from multi-line to single-line causes a content
  // shift that triggers another scroll event. A short cooldown after each
  // toggle lets the browser settle before we re-evaluate.
  useEffect(() => {
    const sentinel = sentinelRef.current;
    const heading = headingRef.current;
    const bar = stickyBarRef.current;
    if (!sentinel || !heading || !bar) return;
    let wasCollapsed = false;
    let cooldown = false;
    const check = () => {
      if (cooldown) return;
      const shouldCollapse = sentinel.getBoundingClientRect().bottom <= 0;
      if (shouldCollapse === wasCollapsed) return;
      wasCollapsed = shouldCollapse;
      if (shouldCollapse) {
        heading.classList.remove("break-words");
        heading.classList.add("truncate");
        bar.style.overflow = "hidden";
        bar.style.height = bar.scrollHeight + "px";
      } else {
        heading.classList.remove("truncate");
        heading.classList.add("break-words");
        bar.style.overflow = "";
        bar.style.height = "";
      }
      cooldown = true;
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          cooldown = false;
        });
      });
    };
    window.addEventListener("scroll", check, { passive: true });
    check();
    return () => window.removeEventListener("scroll", check);
  }, []);

  // Populate and focus contentEditable heading when entering edit mode.
  //
  // Why contentEditable instead of <textarea>?
  //   A <textarea> with font-size:24px/line-height:24px has an intrinsic
  //   minimum height of ~28px (browser adds internal block padding that CSS
  //   cannot override). This causes a 4px layout shift when toggling between
  //   view (<h1>) and edit (<textarea>). A contentEditable <h1> respects
  //   line-height:24px exactly, so the bar stays at 48px in both modes.
  //
  // Why set textContent in the effect instead of React children?
  //   React re-renders children on every state update. For a contentEditable
  //   element, this fights with the browser's cursor/selection state — text
  //   gets reversed or the cursor jumps. Instead, we set textContent once
  //   when entering edit mode, then let the DOM own the content. The onInput
  //   handler syncs DOM → React state (for save), but React never pushes
  //   state back into the DOM.
  useEffect(() => {
    if (editing && nameRef.current) {
      const el = nameRef.current;
      el.textContent = name;
      el.focus();
      // Place cursor at end
      const range = document.createRange();
      range.selectNodeContents(el);
      range.collapse(false);
      const sel = window.getSelection();
      sel?.removeAllRanges();
      sel?.addRange(range);
    }
  }, [editing]);

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
      const { data, error } = await apiClient.POST("/api/v1/menu-items/", {
        body: { name, body },
      });
      if (error || !data) {
        setSaving(false);
        return;
      }
      await queryClient.invalidateQueries({
        queryKey: ["get", "/api/v1/menu-items/"],
      });
      router.replace(`/menu-items/${data.id}`);
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

  const handleMoreAction = useCallback(
    async (action: "togglePlan" | "toggleArchive") => {
      setMoreOpen(false);
      setMoreLoading(true);

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

      setMoreLoading(false);
    },
    [appUser, itemId, inPlan, isArchived, queryClient],
  );

  function handleBack() {
    if (editing && dirty) {
      const confirmed = window.confirm(
        "You have unsaved changes. Discard?",
      );
      if (!confirmed) return;
    }
    router.back();
  }

  // Show more button only for existing saved items
  const showMoreButton = !isNew;
  // Show edit button only in view mode for existing items
  const showEditButton = !isNew && !editing;

  return (
    <div className="flex min-h-screen flex-col [overflow-anchor:none]">
      {/* TopBar — scrolls away (not sticky). The observer watches this
          element; when it leaves the viewport the sticky heading truncates. */}
      <div ref={sentinelRef}>
        <TopBar showBack onBack={handleBack} />
      </div>

      {/* Heading row — always sticky, truncates when TopBar scrolls out */}
      <div
        ref={stickyBarRef}
        className="sticky top-0 relative border-b border-black bg-white z-50"
      >
        <div className="flex items-start gap-3">
          {/* Name — contentEditable in edit mode */}
          {editing ? (
            <h1
              ref={nameRef}
              contentEditable
              suppressContentEditableWarning
              onInput={(e) => handleFormChange("name", e.currentTarget.textContent || "")}
              className="flex-1 min-w-0 p-3 text-2xl font-bold tracking-heading uppercase leading-6 break-words outline-none empty:before:content-[attr(data-placeholder)] empty:before:text-gray-300"
              data-placeholder={isNew ? "Dish..." : "Item name"}
            />
          ) : (
            <h1
              ref={headingRef}
              className="flex-1 min-w-0 p-3 text-2xl font-bold tracking-heading uppercase leading-6 break-words"
            >
              {name || "Untitled"}
            </h1>
          )}

          {/* Edit button — only in view mode for existing items */}
          {showEditButton && (
            <button onClick={handleEdit} className="flex h-12 items-center justify-center px-3 bg-black shrink-0">
              <Icon name="edit" size={24} className="text-white" />
            </button>
          )}

          {/* More button — only for existing saved items */}
          {showMoreButton && (
            <button
              ref={moreRef}
              onClick={() => (moreLoading ? null : setMoreOpen(!moreOpen))}
              className="flex h-12 items-center justify-center px-3 bg-black shrink-0"
            >
              {moreLoading ? (
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
              ) : (
                <Icon name="more_horiz" size={24} className="text-white" />
              )}
            </button>
          )}
        </div>

        {/* More popup — anchored top-right to the more button */}
        {moreOpen && (
          <div className="absolute right-0 top-full z-50 border border-neutral-800 bg-white p-4 shadow-lg">
            <div className="flex flex-col gap-3">
              <label className={`flex items-center gap-3 text-xs font-bold tracking-label uppercase ${isArchived ? "opacity-30" : "cursor-pointer"}`}>
                <input
                  type="checkbox"
                  checked={inPlan}
                  disabled={isArchived}
                  onChange={() => handleMoreAction("togglePlan")}
                  className="h-4 w-4 appearance-none border-2 border-neutral-400 checked:border-black checked:bg-black checked:shadow-[inset_0_0_0_2px_white]"
                />
                In meal plan
              </label>
              <label className="flex items-center gap-3 text-xs font-bold tracking-label uppercase cursor-pointer">
                <input
                  type="checkbox"
                  checked={isArchived}
                  onChange={() => handleMoreAction("toggleArchive")}
                  className="h-4 w-4 appearance-none border-2 border-neutral-400 checked:border-black checked:bg-black checked:shadow-[inset_0_0_0_2px_white]"
                />
                Archived
              </label>
            </div>
          </div>
        )}
      </div>

      {/* Content */}
      <main className={`flex-1 p-3 ${editing ? "flex flex-col" : ""}`}>
        {editing ? (
          <textarea
            value={body}
            onChange={(e) => handleFormChange("body", e.target.value)}
            placeholder="Recipe..."
            className="flex-1 w-full resize-none bg-transparent text-base font-medium leading-6 outline-none placeholder:text-gray-300"
          />
        ) : (
          <article className="prose prose-sm max-w-none font-mono">
            <Markdown>{body || "*No content yet*"}</Markdown>
          </article>
        )}
      </main>

      {/* Save bar — only in edit mode */}
      {editing && (
        <button
            onClick={handleSave}
            disabled={saving || !name.trim()}
            className="sticky bottom-0 flex w-full items-center justify-center p-3 border-t border-black bg-black text-2xl font-bold tracking-label uppercase leading-6 text-white disabled:opacity-30"
          >
            {saving ? "Saving..." : "Save"}
          </button>
      )}

      {/* Click outside to close more popup */}
      {moreOpen && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => setMoreOpen(false)}
        />
      )}
    </div>
  );
}
