export const dynamic = "force-dynamic";

export default function AuthenticatedLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  console.log("[AuthenticatedLayout] render");
  return <div className="flex flex-1 flex-col">{children}</div>;
}
