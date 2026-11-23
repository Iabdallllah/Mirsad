import { Globe } from "lucide-react";
import { createClient } from "@/lib/supabase/server";
import { PageHeader } from "@/components/ui/page-header";
import { EmptyState } from "@/components/ui/empty-state";
import { ButtonLink } from "@/components/ui/button";
import { domainQuotaLabel } from "@/lib/quota";

export const metadata = { title: "Domains" };

export default async function DomainsPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  const { data: membership } = await supabase
    .from("workspace_members")
    .select("workspace_id")
    .eq("user_id", user?.id ?? "")
    .limit(1)
    .maybeSingle();

  const [{ data: domains }, { data: limits }] = membership
    ? await Promise.all([
        supabase
          .from("domains")
          .select("id, name, environment, verification_status, next_scan_at")
          .eq("workspace_id", membership.workspace_id)
          .order("name"),
        supabase
          .from("plan_limits")
          .select("domains_limit")
          .eq("workspace_id", membership.workspace_id)
          .maybeSingle(),
      ])
    : [{ data: [] }, { data: null }];

  const list = domains ?? [];
  const limit = (limits?.domains_limit as number | undefined) ?? 2;

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Domains"
        subtitle={domainQuotaLabel(list.length, limit)}
        actions={
          <ButtonLink href="/domains/new" data-testid="add-domain">
            Add domain
          </ButtonLink>
        }
      />

      {list.length === 0 ? (
        <EmptyState
          icon={Globe}
          title="Add your first domain"
          description="Beta workspaces can register two domains (for example, staging and production of the same project). Ownership must be verified before any scan runs."
          action={
            <ButtonLink href="/domains/new" data-testid="add-domain-empty">
              Add domain
            </ButtonLink>
          }
        />
      ) : (
        <div className="overflow-hidden rounded-lg border border-border">
          <table className="w-full text-left text-sm">
            <caption className="sr-only">Registered domains</caption>
            <thead className="bg-surface-2 text-xs uppercase tracking-wide text-text-muted">
              <tr>
                <th scope="col" className="px-4 py-3 font-medium">
                  Domain
                </th>
                <th scope="col" className="px-4 py-3 font-medium">
                  Environment
                </th>
                <th scope="col" className="px-4 py-3 font-medium">
                  Verification
                </th>
                <th scope="col" className="px-4 py-3 font-medium">
                  Next scan
                </th>
              </tr>
            </thead>
            <tbody>
              {list.map((domain) => (
                <tr key={domain.id} className="border-t border-border bg-surface-1">
                  <td className="px-4 py-3 font-mono text-xs text-text">{domain.name}</td>
                  <td className="px-4 py-3 capitalize text-text-muted">{domain.environment}</td>
                  <td className="px-4 py-3 capitalize text-text-muted">
                    {domain.verification_status}
                  </td>
                  <td className="px-4 py-3 text-text-muted">
                    {domain.next_scan_at
                      ? new Date(domain.next_scan_at).toLocaleString()
                      : "Not scheduled"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className="text-xs text-text-muted">
        Domain creation, DNS/file verification, and deletion flows arrive in Phase 3 (web product)
        per plan.md §3.2. This table is intentionally read-only in Phase 0.
      </p>
    </div>
  );
}
