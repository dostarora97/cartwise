"use client";

import { useParams } from "next/navigation";
import { MenuItemPage } from "@/components/menu-item-page";

export default function MenuItemDetailPage() {
  const { id } = useParams<{ id: string }>();
  return <MenuItemPage itemId={id} />;
}
