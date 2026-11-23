/** Layout-preserving skeleton placeholder (design.md §7.3, §12). */
export function Skeleton({ className = "" }: { className?: string }) {
  return (
    <div
      aria-hidden="true"
      className={`animate-pulse rounded-md bg-surface-2 ${className}`}
    />
  );
}
