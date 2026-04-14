import Link from "next/link";

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col">
      <main className="flex flex-1 flex-col items-center justify-center p-3">
        <span className="text-2xl font-bold tracking-heading uppercase leading-6">
          Not found
        </span>
        <p className="mt-3 text-base leading-6 text-gray-500">
          The page you&apos;re looking for doesn&apos;t exist.
        </p>
      </main>
      <Link
        href="/meal-plan"
        className="sticky bottom-0 flex w-full items-center justify-center p-3 border-t border-black bg-black text-2xl font-bold tracking-label uppercase leading-6 text-white"
      >
        Go home
      </Link>
    </div>
  );
}
