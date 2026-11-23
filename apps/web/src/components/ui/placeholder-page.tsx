import { PageHeader } from "@/components/ui/page-header";
import { Alert } from "@/components/ui/alert";
import { EmptyState } from "@/components/ui/empty-state";
import { ButtonLink } from "@/components/ui/button";
import { type LucideIcon } from "lucide-react";

type PlaceholderPageProps = {
  title: string;
  subtitle: string;
  phase: string;
  icon: LucideIcon;
  emptyTitle: string;
  emptyDescription: string;
  cta?: { href: string; label: string };
  testId?: string;
};

/**
 * Honest Phase 0 placeholder for a planned route: renders the page shell and
 * an explicit "arrives in Phase N" notice instead of fabricated data. Keeps
 * navigation complete and deep links valid (design.md §4.3).
 */
export function PlaceholderPage({
  title,
  subtitle,
  phase,
  icon,
  emptyTitle,
  emptyDescription,
  cta,
  testId,
}: PlaceholderPageProps) {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader title={title} subtitle={subtitle} />
      <Alert variant="info" title={`${title} arrives in ${phase}`}>
        This route is scaffolded in Phase 0 (Foundation). It ships with the milestone that builds
        its data, so no placeholder numbers or sample findings are shown.
      </Alert>
      <EmptyState
        icon={icon}
        title={emptyTitle}
        description={emptyDescription}
        testId={testId}
        action={cta ? <ButtonLink href={cta.href}>{cta.label}</ButtonLink> : undefined}
      />
    </div>
  );
}
