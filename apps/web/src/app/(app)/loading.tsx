import { Skeleton } from "@/components/ui/skeleton";

/** Layout-preserving skeleton for any app route (design.md §13.1). */
export default function AppLoading() {
  return (
    <div aria-busy="true" aria-label="Loading page" className="flex flex-col gap-6">
      <div className="border-b border-border pb-6">
        <Skeleton className="h-9 w-56" />
        <Skeleton className="mt-3 h-4 w-96 max-w-full" />
      </div>
      <Skeleton className="h-40 w-full rounded-lg" />
      <Skeleton className="h-64 w-full rounded-lg" />
    </div>
  );
}
