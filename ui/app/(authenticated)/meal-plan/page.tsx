"use client";

import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/utils";
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

      <div className="flex items-stretch justify-between border-b border-black">
        <span className="flex items-center p-3 text-2xl font-bold tracking-label uppercase leading-6">
          Meal Plan
        </span>
        {hasItems && (
          <button onClick={() => router.push("/meal-plan/edit")} aria-label="Edit meal plan" className="flex items-center justify-center p-3 bg-black">
            <Icon name="edit" size={24} className="text-white" />
          </button>
        )}
      </div>

      <main
        className={cn("flex-1", !hasItems && "flex items-center justify-center")}
      >
        {isLoading ? null : !hasItems ? (
          <button
            onClick={() => router.push("/meal-plan/edit")}
            aria-label="Create meal plan"
            className="flex h-14 w-14 items-center justify-center bg-black text-white text-4xl"
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
          aria-label="New expense"
          className="fixed bottom-12 right-12 flex h-14 w-14 items-center justify-center bg-black text-white"
        >
          <Icon name="receipt_long" size={24} />
        </button>
      )}
    </div>
  );
}
