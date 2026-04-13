"use client";

import { useAuth } from "@/lib/auth";
import { $api } from "@/lib/api/hooks";
import { TopBar } from "@/components/top-bar";
import { Icon } from "@/components/icon";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

export default function HomePage() {
  const { session, appUser, loading } = useAuth();
  const router = useRouter();

  const { data: mealPlan } = $api.useQuery(
    "get",
    "/api/v1/meal-plans/{user_id}",
    { params: { path: { user_id: appUser?.id ?? "" } } },
    { enabled: !!appUser },
  );

  useEffect(() => {
    if (loading) return;
    if (!session) {
      router.replace("/login");
    } else if (!appUser) {
      router.replace("/onboarding");
    }
  }, [session, appUser, loading, router]);

  if (loading || !session || !appUser) {
    return <div className="flex min-h-screen items-center justify-center" />;
  }

  const items = mealPlan?.items ?? [];

  return (
    <div className="flex min-h-screen flex-col">
      <TopBar />

      <div className="flex items-center justify-between border-b border-black px-6 py-4">
        <span className="text-sm font-bold tracking-[0.2em] uppercase">
          Meal Plan
        </span>
        <button onClick={() => router.push("/meal-plan/edit")}>
          <Icon name="edit" size={20} />
        </button>
      </div>

      <main className="flex-1 px-6">
        {items.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20">
            <button
              onClick={() => router.push("/meal-plan/edit")}
              className="text-6xl text-gray-300 hover:text-black transition-colors"
            >
              +
            </button>
          </div>
        ) : (
          <ul>
            {items.map((item) => (
              <li
                key={item.menu_item.id}
                className="border-b border-gray-200 py-5"
              >
                <button
                  onClick={() =>
                    router.push(`/menu-items/${item.menu_item.id}`)
                  }
                  className="w-full text-left"
                >
                  <span className="text-sm font-medium tracking-[0.15em] uppercase">
                    - {item.menu_item.name}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </main>

      {items.length > 0 && (
        <div className="sticky bottom-0 border-t border-black bg-white px-6 py-4">
          <button
            onClick={() => router.push("/invoice")}
            className="flex w-full items-center justify-center gap-3 bg-black py-4 text-sm font-bold tracking-[0.2em] uppercase text-white"
          >
            <Icon name="description" size={20} />
            Add Invoice
          </button>
        </div>
      )}
    </div>
  );
}
