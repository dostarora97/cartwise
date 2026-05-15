"use client";

import { useAuth } from "@/lib/auth";
import { ErrorBody } from "@/components/error-body";
import { Spinner } from "@/components/spinner";

export default function AuthenticatedLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { appUser, loading, error, refreshAppUser } = useAuth();

  if (loading || (!appUser && !error)) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center">
        <Spinner />
      </div>
    );
  }

  if (error || !appUser) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center p-3">
        <ErrorBody message="Something went wrong." onRetry={refreshAppUser} />
      </div>
    );
  }

  return <div className="flex flex-1 flex-col">{children}</div>;
}
