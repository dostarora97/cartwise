"use client";

import { useAuth } from "@/lib/auth";
import { $api } from "@/lib/api/hooks";
import { TopBar } from "@/components/top-bar";
import { MealPlanItem } from "@/components/meal-plan-item";
import { Icon } from "@/components/icon";
import { useRouter } from "next/navigation";

export default function MealPlanPage() {
  const { appUser } = useAuth();
  const router = useRouter();

  const { data: mealPlan, isLoading } = $api.useQuery(
    "get",
    "/api/v1/meal-plans/{user_id}",
    { params: { path: { user_id: appUser!.id } } },
  );

  const items = mealPlan?.items ?? [];
  const hasItems = items.length > 0;

  return (
    <div className="flex min-h-screen flex-col">
      <TopBar />

      <div className="flex h-12 items-center justify-between border-b border-black px-6">
        <span className="text-sm font-bold tracking-label uppercase">
          Meal Plan
        </span>
        {hasItems && (
          <button onClick={() => router.push("/meal-plan/edit")}>
            <Icon name="edit" size={20} />
          </button>
        )}
      </div>

      <main
        className={`flex-1 px-6 ${!hasItems ? "flex items-center justify-center" : ""}`}
      >
        {isLoading ? null : !hasItems ? (
          <button
            onClick={() => router.push("/meal-plan/edit")}
            className="text-6xl text-gray-300 hover:text-black transition-colors"
          >
            +
          </button>
        ) : (
          <ul>
            {items.map((item) => (
              <MealPlanItem
                key={item.menu_item.id}
                name={item.menu_item.name}
                mode="view"
                onTap={() =>
                  router.push(`/menu-items/${item.menu_item.id}`)
                }
              />
            ))}
          </ul>
        )}
      </main>

      {hasItems && (
        <button
          onClick={() => router.push("/invoice")}
          className="fixed bottom-6 right-6 flex h-14 w-14 items-center justify-center border border-neutral-800 bg-neutral-800 text-white"
        >
          <Icon name="receipt_long" size={24} />
        </button>
      )}
    </div>
  );
}
