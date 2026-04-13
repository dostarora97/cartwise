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
  const hasItems = items.length > 0;

  return (
    <div className="flex min-h-screen flex-col">
      <TopBar />

      <div className="flex items-center justify-between border-b border-black px-6 py-4">
        <span className="text-sm font-bold tracking-label uppercase">
          Meal Plan
        </span>
        {hasItems && (
          <button onClick={() => router.push("/meal-plan/edit")}>
            <Icon name="edit" size={20} />
          </button>
        )}
      </div>

      <main className={`flex-1 px-6 ${!hasItems ? "flex items-center justify-center" : ""}`}>
        {!hasItems ? (
          <button
            onClick={() => router.push("/meal-plan/edit")}
            className="text-6xl text-gray-300 hover:text-black transition-colors"
          >
            +
          </button>
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
                  <span className="text-sm font-medium tracking-item">
                    - {item.menu_item.name}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </main>

      {hasItems && (
        <button
          onClick={() => router.push("/invoice")}
          className="fixed bottom-6 right-6 flex h-14 w-14 items-center justify-center border border-gray-800 bg-gray-800 text-white"
        >
          <Icon name="receipt_long" size={24} />
        </button>
      )}
    </div>
  );
}
