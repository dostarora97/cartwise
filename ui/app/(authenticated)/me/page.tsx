"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useRequiredAuth } from "@/lib/auth";

export default function MePage() {
  const { appUser } = useRequiredAuth();
  const router = useRouter();

  useEffect(() => {
    router.replace(`/user/${appUser.id}`);
  }, [appUser.id, router]);

  return null;
}
