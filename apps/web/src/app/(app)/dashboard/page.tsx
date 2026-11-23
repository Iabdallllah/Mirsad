import Link from "next/link";
import { redirect } from "next/navigation";
import { Globe, Radar, ShieldCheck } from "lucide-react";
import { createClient } from "@/lib/supabase/server";
import { PageHeader } from "@/components/ui/page-header";
import { EmptyState } from "@/components/ui/empty-state";
import { ButtonLink } from "@/components/ui/button";
import { Alert } from "@/components/ui/alert";

export const metadata = { title: "Dashboard" };

type DashboardPageProps = {
  searchParams: Promise<{ domain?: string }>;
};

/**
 * Dashboard (design.md §6.3): the 10-second answer to "what is my security
 * state?". Phase 0 renders honest empty states — no fabricated scores
 * (plan.md §3.2 Phase 0 exit criteria; design.md J6 zero-findings honesty).
 */
export default async function DashboardPage({ searchParams }: DashboardPageProps) {
  const { domain: domainFilter } = await searchParams;
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) redirect("/sign-in");

  const { data: membership } = await supabase
    .from("workspace_members")
    .select("workspace_id")
    .eq("user_id", user.id)
    .limit(1)
    .maybeSingle();

  if (!membership) {
    return (
      <Alert variant="warning" title="Workspace setup incomplete">
        Your workspace is being provisioned. Reload in a moment or contact support with your
        request ID.
      </Alert>
    );
  }

  const workspaceId = membership.workspace_id as string;

  const domainsQuery = supabase
    .from("domains")
    .select("id, name, verification_status")
    .eq("workspace_id", workspaceId)
    .order("name");

  const [{ data: domains }, { data: latestScans }] = await Promise.all([
    domainsQuery,
    supabase
      .from("scans")
      .select("id, status, finished_at, domain_id")
      .eq("workspace_id", workspaceId)
      .order("created_at", { ascending: false })
      .limit(1),
  ]);

  const allDomains = domains ?? [];
  const latestScan = latestScans?.[0];
  const hasDomains = allDomains.length > 0;
  const verifiedDomains = allDomains.filter((d) => d.verification_status === "verified");
  const canRunScan = verifiedDomains.length > 0;
  const scanHref = canRunScan
    ? `/domains/${verifiedDomains[0].id}?action=scan`
    : hasDomains
      ? `/domains/${allDomains[0].id}`
      : "/domains/new";

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Dashboard"
        subtitle="Evidence over assurance — what was tested, found, fixed, and verified."
        actions={
          <ButtonLink
            href={scanHref}
            data-testid="run-scan"
            aria-disabled={!canRunScan}
            title={canRunScan ? "Run a scan" : "Verify a domain before running scans"}
            className={!canRunScan ? "pointer-events-none opacity-50" : undefined}
          >
            <Radar aria-hidden="true" className="size-4" />
            Run scan
          </ButtonLink>
        }
      />

      {!hasDomains ? (
        <EmptyState
          icon={Globe}
          testId="dashboard-empty"
          title="Add your first domain"
          description="Verify ownership of a staging or production domain, then run your first scan. Live logs appear within 30 seconds of starting."
          action={
            <ButtonLink href="/domains/new" data-testid="add-domain">
              Add domain
            </ButtonLink>
          }
        />
      ) : !canRunScan ? (
        <EmptyState
          icon={ShieldCheck}
          title="Verify your domain"
          description="A domain must be verified before any scan can run. Open the domain to complete DNS TXT or file verification, then start your first scan."
          action={
            <ButtonLink href={scanHref} data-testid="verify-domain">
              Verify domain
            </ButtonLink>
          }
        />
      ) : !latestScan ? (
        <EmptyState
          icon={Radar}
          title="Run your first scan"
          description="Your domain is verified. Start a scan to see confirmed issues with sanitized evidence and an honest coverage receipt."
          action={
            <ButtonLink href={scanHref} data-testid="run-scan-empty">
              Run your first scan
            </ButtonLink>
          }
        />
      ) : (
        <>
          <section aria-labelledby="kpi-heading" className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <h2 id="kpi-heading" className="sr-only">
              Security overview
            </h2>
            <KpiCard
              label="Security Score"
              value="Unscored"
              context="No completed scored scan yet. Scores appear only after verified coverage."
            />
            <KpiCard
              label="Open critical / high issues"
              value="—"
              context="Issue scoring lands with the scan engine (Phase 1)."
            />
            <KpiCard
              label="Pending PRs"
              value="—"
              context="PR mirroring lands with the GitHub loop (Phase 2)."
            />
            <KpiCard
              label="Last scan"
              value={latestScan.status as string}
              context={`Domain filter: ${domainFilter ?? "all domains"}.`}
            />
          </section>

          {domainFilter ? (
            <p className="text-sm text-text-muted">
              Showing context for one domain.{" "}
              <Link href="/dashboard" className="text-accent underline-offset-4 hover:underline">
                Clear domain filter
              </Link>
            </p>
          ) : null}

          <section
            aria-labelledby="posture-heading"
            className="rounded-lg border border-border bg-surface-1 p-6"
          >
            <h2 id="posture-heading" className="text-lg font-semibold text-text">
              Posture trend
            </h2>
            <p className="mt-1 text-sm text-text-muted">
              Score over time appears after two scored scans. Until then, no trend is shown rather
              than an invented one.
            </p>
          </section>

          <section
            aria-labelledby="honesty-heading"
            className="rounded-lg border border-border bg-surface-1 p-6"
          >
            <h2 id="honesty-heading" className="flex items-center gap-2 text-lg font-semibold text-text">
              <ShieldCheck aria-hidden="true" className="size-5 text-accent" />
              Coverage, not guarantees
            </h2>
            <p className="mt-1 max-w-prose text-sm text-text-muted">
              Every completed scan ships with a Coverage Receipt that lists what was tested,
              attempted, and missed. &ldquo;No findings&rdquo; means no vulnerabilities were
              detected within tested scope — never that a system is 100% secure.
            </p>
            <p className="mt-3 text-xs text-text-muted">
              Coverage Receipts become available with the scan engine (Phase 1).
            </p>
          </section>
        </>
      )}
    </div>
  );
}

function KpiCard({
  label,
  value,
  context,
}: {
  label: string;
  value: string;
  context: string;
}) {
  return (
    <div className="rounded-lg border border-border bg-surface-1 p-5">
      <p className="text-xs font-medium uppercase tracking-wide text-text-muted">{label}</p>
      <p className="mt-2 font-display text-2xl font-semibold text-text tabular-nums">{value}</p>
      <p className="mt-2 text-xs text-text-muted">{context}</p>
    </div>
  );
}
