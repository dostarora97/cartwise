"use client";

import { useState, useEffect, useMemo } from "react";
import { useRequiredAuth } from "@/lib/auth";
import { Icon } from "@/components/icon";
import { Spinner } from "@/components/spinner";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface SwiggyOrder {
  orderId: string;
  restaurantName: string;
  orderDate: string;
  totalAmount: number;
  status: string;
}

interface SwiggyOrderPickerProps {
  selectedOrderId: string | null;
  onSelect: (orderId: string | null) => void;
}

export function SwiggyOrderPicker({
  selectedOrderId,
  onSelect,
}: SwiggyOrderPickerProps) {
  const { appUser, session } = useRequiredAuth();

  if (!appUser.swiggy_connected) {
    return <ConnectCTA />;
  }

  return (
    <OrderList
      selectedOrderId={selectedOrderId}
      onSelect={onSelect}
      accessToken={session?.access_token ?? null}
    />
  );
}

function ConnectCTA({ message }: { message?: string }) {
  const { session } = useRequiredAuth();
  const [connecting, setConnecting] = useState(false);

  async function handleConnect() {
    if (!session?.access_token) return;
    setConnecting(true);
    console.log("[SwiggyConnect] handleConnect: starting OAuth flow");

    try {
      const resp = await fetch(`${API_BASE}/api/v1/auth/swiggy/connect`, {
        method: "POST",
        headers: { Authorization: `Bearer ${session.access_token}` },
      });

      console.log("[SwiggyConnect] /auth/swiggy/connect response:", {
        status: resp.status,
        statusText: resp.statusText,
        headers: Object.fromEntries(resp.headers.entries()),
      });

      if (!resp.ok) {
        const errorBody = await resp.text();
        console.error("[SwiggyConnect] connect failed:", { status: resp.status, body: errorBody });
        throw new Error("Failed to start connection");
      }

      const data = await resp.json();
      console.log("[SwiggyConnect] connect response data:", {
        authorize_url: data.authorize_url,
        redirect_uri: data.redirect_uri,
        code_verifier_length: data.code_verifier?.length,
      });

      // Store code_verifier in cookie for the callback
      document.cookie = `swiggy_code_verifier=${data.code_verifier}; path=/; max-age=600; SameSite=Lax`;
      console.log("[SwiggyConnect] code_verifier stored in cookie, redirecting to:", data.authorize_url);

      // Redirect to Swiggy OAuth
      window.location.href = data.authorize_url;
    } catch (e) {
      console.error("[SwiggyConnect] handleConnect error:", e);
      setConnecting(false);
    }
  }

  return (
    <div className="flex flex-col items-center justify-center gap-3 p-6 text-center">
      {message && <p className="text-sm text-gray-600">{message}</p>}
      <button
        onClick={handleConnect}
        disabled={connecting}
        className="flex items-center justify-center px-6 h-12 bg-black text-white text-base font-bold tracking-label uppercase disabled:bg-neutral-400"
      >
        {connecting ? (
          <div className="size-5 animate-spin rounded-full border-[3px] border-white border-t-transparent" />
        ) : (
          "Connect Swiggy"
        )}
      </button>
    </div>
  );
}

function OrderList({
  selectedOrderId,
  onSelect,
  accessToken,
}: {
  selectedOrderId: string | null;
  onSelect: (orderId: string | null) => void;
  accessToken: string | null;
}) {
  const [orders, setOrders] = useState<SwiggyOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [needsReauth, setNeedsReauth] = useState(false);
  const [search, setSearch] = useState("");

  async function fetchOrders() {
    if (!accessToken) return;
    setLoading(true);
    setError(null);
    setNeedsReauth(false);
    console.log("[SwiggyOrders] fetchOrders: starting");

    try {
      const resp = await fetch(`${API_BASE}/api/v1/orders/swiggy/orders`, {
        headers: { Authorization: `Bearer ${accessToken}` },
      });

      console.log("[SwiggyOrders] /orders/swiggy/orders response:", {
        status: resp.status,
        statusText: resp.statusText,
        headers: Object.fromEntries(resp.headers.entries()),
      });

      if (resp.status === 422) {
        const body = await resp.json().catch(() => ({}));
        console.log("[SwiggyOrders] 422 response body:", body);
        if (body.provider === "swiggy") {
          setNeedsReauth(true);
          return;
        }
      }

      if (!resp.ok) {
        const errorBody = await resp.text();
        console.error("[SwiggyOrders] fetch failed:", { status: resp.status, body: errorBody });
        throw new Error(`HTTP ${resp.status}`);
      }

      const data = await resp.json();
      console.log("[SwiggyOrders] orders received:", { count: data.length, orders: data });
      setOrders(data);
    } catch (e) {
      console.error("[SwiggyOrders] fetchOrders error:", e);
      setError(e instanceof Error ? e.message : "Failed to fetch orders");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchOrders();
  }, [accessToken]); // eslint-disable-line react-hooks/exhaustive-deps

  const filtered = useMemo(() => {
    if (!search) return orders;
    const q = search.toLowerCase();
    return orders.filter(
      (o) =>
        o.orderId.toLowerCase().includes(q) ||
        o.restaurantName.toLowerCase().includes(q),
    );
  }, [orders, search]);

  if (needsReauth) {
    return (
      <ConnectCTA message="Session expired — reconnect Swiggy." />
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center p-6">
        <Spinner />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center gap-3 p-6 text-center">
        <p className="text-xs text-red-600 tracking-wider">{error}</p>
        <button
          onClick={fetchOrders}
          className="border border-black px-4 py-2 text-sm font-bold tracking-label uppercase"
        >
          Retry
        </button>
      </div>
    );
  }

  // Selected state — collapsed single row
  if (selectedOrderId) {
    const selected = orders.find((o) => o.orderId === selectedOrderId);
    return (
      <div className="flex items-stretch border-b border-gray-200 bg-black text-white">
        <div className="flex flex-1 items-center p-3 text-base leading-6 font-bold tracking-label">
          <span>#{selectedOrderId}</span>
          <span className="ml-auto">&#8377;{selected?.totalAmount ?? "—"}</span>
        </div>
        <button
          type="button"
          onClick={() => onSelect(null)}
          aria-label="Deselect order"
          className="flex items-center justify-center p-3"
        >
          <Icon name="close" size={20} className="text-white" />
        </button>
      </div>
    );
  }

  // Unselected state — list
  return (
    <div>
      <div className="flex items-center gap-2 p-3 border-b border-gray-200">
        <Icon name="search" size={20} className="text-gray-400" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="flex-1 text-base leading-6 outline-none bg-transparent"
        />
      </div>

      {filtered.length === 0 ? (
        <p className="p-3 text-sm text-gray-500">No orders found</p>
      ) : (
        <div>
          {filtered.map((order) => (
            <button
              key={order.orderId}
              type="button"
              onClick={() => onSelect(order.orderId)}
              className="flex w-full items-center p-3 text-base leading-6 border-b border-gray-200 hover:bg-gray-50"
            >
              <span className="tracking-label">
                #{order.orderId}
              </span>
              <span className="ml-auto font-bold tracking-label">&#8377;{order.totalAmount}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
