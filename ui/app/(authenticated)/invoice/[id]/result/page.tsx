"use client";

import { useMemo } from "react";
import { notFound, useParams, useRouter } from "next/navigation";
import { $api } from "@/lib/api/hooks";
import { cn } from "@/lib/utils";
import { TopBar } from "@/components/top-bar";
import { Chip } from "@/components/chip";

interface GroceryItem {
  upc: string;
  description: string;
  total: number;
}

export default function SplitResultPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();

  const { data: order, isLoading, isError } = $api.useQuery(
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

  // Sort splits: by group size ascending, then by sorted concatenated names
  const sortedSplits = useMemo(() => {
    if (!order?.splits) return [];

    function resolveName(id: string) {
      return userMap.get(id) ?? id;
    }

    return [...order.splits]
      .map((split) => ({
        ...split,
        _sortedItems: ([...(split.grocery_items ?? [])] as unknown as GroceryItem[]).sort(
          (a, b) => a.description.localeCompare(b.description),
        ),
        _sortedMemberIds: [...split.member_ids].sort((a, b) =>
          resolveName(a).localeCompare(resolveName(b)),
        ),
      }))
      .sort((a, b) => {
        const sizeDiff = a.member_ids.length - b.member_ids.length;
        if (sizeDiff !== 0) return sizeDiff;
        const aNamesKey = a._sortedMemberIds.map(resolveName).join(", ");
        const bNamesKey = b._sortedMemberIds.map(resolveName).join(", ");
        return aNamesKey.localeCompare(bNamesKey);
      });
  }, [order, userMap]);

  if (isLoading) {
    return (
      <div className="flex min-h-screen flex-col">
        <TopBar showBack onBack={() => router.push("/meal-plan")} />
        <div className="flex items-center p-3 border-b border-black">
          <span className="text-2xl font-bold tracking-label uppercase leading-6">
            Split result
          </span>
        </div>
        <main className="flex-1" />
      </div>
    );
  }
  if (!order && !isError) notFound();

  return (
    <div className="flex min-h-screen flex-col">
      <TopBar showBack onBack={() => router.push("/meal-plan")} />

      <div className="flex items-center p-3 border-b border-black">
        <span className="text-2xl font-bold tracking-label uppercase leading-6">
          Split result
        </span>
      </div>

      <main className="flex-1">
        {sortedSplits.map((split) => {
          const isSuccess = split.status === "success";

          return (
            <div
              key={split.id}
              className={cn(
                "border-b border-black last:border-b-0",
                isSuccess ? "bg-green-50" : "bg-red-50",
              )}
            >
              <div className="flex items-center gap-1 flex-wrap p-3">
                {split._sortedMemberIds.map((mid) => (
                  <Chip key={mid} label={userMap.get(mid) ?? mid} />
                ))}
                <span className="ml-auto text-2xl font-bold leading-6">
                  ₹{split.amount.toFixed(2)}
                </span>
              </div>
              {split._sortedItems.map((item, ii) => (
                <div
                  key={`${item.upc}-${ii}`}
                  className="flex items-center p-3 border-t border-gray-200"
                >
                  <span className="flex-1 text-base leading-6 truncate">
                    {item.description}
                  </span>
                </div>
              ))}
            </div>
          );
        })}
      </main>

      <button
        onClick={() => router.push("/meal-plan")}
        className="sticky bottom-0 flex w-full items-center justify-center p-3 border-t border-black bg-black text-2xl font-bold tracking-label uppercase leading-6 text-white"
      >
        OK
      </button>
    </div>
  );
}
