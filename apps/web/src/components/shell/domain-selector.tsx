"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";

type DomainOption = { id: string; name: string };

type DomainSelectorProps = {
  domains: DomainOption[];
  compact?: boolean;
  id?: string;
  onNavigate?: () => void;
};

/**
 * Workspace domain context (design.md §4.2–4.3). Filters Dashboard/Issues via
 * the `domain` query parameter so deep links survive refresh. Selecting a
 * domain never triggers a scan; scan actions always require one domain.
 */
export function DomainSelector({ domains, compact = false, id, onNavigate }: DomainSelectorProps) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const current = searchParams.get("domain") ?? "all";

  function onChange(value: string) {
    const params = new URLSearchParams(searchParams.toString());
    if (value === "all") params.delete("domain");
    else params.set("domain", value);
    const query = params.toString();
    router.push(query ? `${pathname}?${query}` : pathname);
    onNavigate?.();
  }

  return (
    <div>
      <label
        htmlFor={id ?? "domain-selector"}
        className={compact ? "sr-only" : "text-xs font-medium uppercase tracking-wide text-text-muted"}
      >
        Domain
      </label>
      <select
        id={id ?? "domain-selector"}
        data-testid="domain-selector"
        value={current}
        onChange={(event) => onChange(event.target.value)}
        className="mt-1 min-h-11 w-full rounded-md border border-border bg-surface-1 px-3 text-sm text-text focus-visible:border-border-strong"
      >
        <option value="all">All domains</option>
        {domains.map((domain) => (
          <option key={domain.id} value={domain.id}>
            {domain.name}
          </option>
        ))}
      </select>
    </div>
  );
}
