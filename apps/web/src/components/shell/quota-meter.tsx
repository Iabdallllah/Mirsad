import { quotaState, quotaLabel } from "@/lib/quota";

type QuotaMeterProps = {
  used: number;
  limit: number;
};

/** Sidebar quota meter: text + progressbar semantics, warning at 80%. */
export function QuotaMeter({ used, limit }: QuotaMeterProps) {
  const state = quotaState(used, limit);
  const percent = limit > 0 ? Math.min(100, Math.round((used / limit) * 100)) : 100;
  const barColor =
    state === "exhausted" ? "bg-critical" : state === "warning" ? "bg-warning" : "bg-accent";

  return (
    <div data-testid="quota-meter" className="rounded-md border border-border bg-surface-1 p-3">
      <div className="flex items-center justify-between gap-2 text-xs text-text-muted">
        <span>Beta quota</span>
        <span className="tabular-nums">
          {used}/{limit}
        </span>
      </div>
      <div
        role="progressbar"
        aria-label={quotaLabel(used, limit)}
        aria-valuemin={0}
        aria-valuemax={limit}
        aria-valuenow={used}
        className="mt-2 h-1.5 overflow-hidden rounded-full bg-surface-2"
      >
        <div className={`h-full rounded-full ${barColor}`} style={{ width: `${percent}%` }} />
      </div>
      <p className="mt-2 text-xs text-text-muted">
        {state === "exhausted"
          ? "Quota reached — scans pause until the reset date."
          : state === "warning"
            ? "Approaching the monthly scan limit."
            : "5 scans per month, shared across domains."}
      </p>
    </div>
  );
}
