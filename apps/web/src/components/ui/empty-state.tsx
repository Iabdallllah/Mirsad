import type { LucideIcon } from "lucide-react";

type EmptyStateProps = {
  icon: LucideIcon;
  title: string;
  description: string;
  action?: React.ReactNode;
  testId?: string;
};

/** Empty state: icon + headline + explanation + one primary CTA (design.md §7.3). */
export function EmptyState({ icon: Icon, title, description, action, testId }: EmptyStateProps) {
  return (
    <div
      className="flex flex-col items-start gap-4 rounded-lg border border-border bg-surface-1 p-6 sm:items-center sm:p-10 sm:text-center"
      data-testid={testId}
    >
      <span className="flex size-11 items-center justify-center rounded-full border border-border-strong bg-surface-2">
        <Icon aria-hidden="true" className="size-5 text-accent" />
      </span>
      <div className="max-w-prose">
        <h2 className="text-lg font-semibold text-text">{title}</h2>
        <p className="mt-1 text-sm text-text-muted">{description}</p>
      </div>
      {action ? <div className="mt-1">{action}</div> : null}
    </div>
  );
}
