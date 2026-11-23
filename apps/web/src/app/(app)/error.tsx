"use client";

import { Button } from "@/components/ui/button";

/**
 * App-wide error boundary: what happened → what to do → request ID → retry
 * (design.md §7.3). No stack traces or internal details are rendered.
 */
export default function AppError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div role="alert" className="rounded-lg border border-critical/40 bg-surface-1 p-6">
      <h1 className="text-xl font-semibold text-text">This page could not load</h1>
      <p className="mt-2 text-sm text-text-muted">
        We could not load this page. Nothing was changed. Retry, or sign in again if the problem
        persists.
      </p>
      {error.digest ? (
        <p className="mt-2 font-mono text-xs text-text-muted">Request ID: {error.digest}</p>
      ) : null}
      <div className="mt-4">
        <Button type="button" onClick={reset}>
          Retry
        </Button>
      </div>
    </div>
  );
}
