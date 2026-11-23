/**
 * Pure quota helpers (unit-tested). Beta limits: 2 domains, 5 scans/month
 * (plan.md §2.3). 80% usage triggers an inline warning (design.md J9).
 */

export type QuotaState = "ok" | "warning" | "exhausted";

export function quotaState(used: number, limit: number): QuotaState {
  if (limit <= 0) return "exhausted";
  const ratio = used / limit;
  if (ratio >= 1) return "exhausted";
  if (ratio >= 0.8) return "warning";
  return "ok";
}

export function quotaLabel(used: number, limit: number): string {
  return `${used} of ${limit} scans used this period`;
}

export function domainQuotaLabel(used: number, limit: number): string {
  const state = quotaState(used, limit);
  const suffix = state === "exhausted" ? " — limit reached" : state === "warning" ? " — nearing limit" : "";
  return `${used} of ${limit} domains${suffix}`;
}
