export function Spinner() {
  return (
    <div className="flex h-14 w-14 items-center justify-center bg-black">
      <div className="size-6 animate-spin motion-reduce:animate-none rounded-full border-[3px] border-white border-t-transparent" />
    </div>
  );
}
