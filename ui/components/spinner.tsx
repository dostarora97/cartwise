export function Spinner() {
  return (
    <div className="flex flex-1 items-center justify-center">
      <div className="size-6 animate-spin motion-reduce:animate-none rounded-full border-2 border-black border-t-transparent" />
    </div>
  );
}
