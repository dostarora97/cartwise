"use client";

import { AuthGuard } from "@/components/auth-guard";
import { TopBar } from "@/components/top-bar";
import { useAuth } from "@/lib/auth";

function HomeContent() {
  const { appUser } = useAuth();

  return (
    <div className="flex min-h-screen flex-col">
      <TopBar />
      <main className="flex-1 p-6">
        <div className="space-y-6">
          <div>
            <h2 className="text-xl font-semibold">
              Welcome, {appUser?.name}
            </h2>
            <p className="text-sm text-muted-foreground">
              Your meal plan and splits will appear here.
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}

export default function HomePage() {
  return (
    <AuthGuard>
      <HomeContent />
    </AuthGuard>
  );
}
