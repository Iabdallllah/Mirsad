import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { MobileDrawer } from "@/components/shell/mobile-drawer";
import { DomainSelector } from "@/components/shell/domain-selector";
import { SidebarContent } from "@/components/shell/sidebar-content";

/**
 * Authenticated app shell (design.md §4.2): fixed 264px sidebar ≥1024px,
 * drawer below. Session comes from Supabase cookies; RLS scopes every query
 * to the signed-in owner.
 */
export default async function AppLayout({ children }: { children: React.ReactNode }) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/sign-in");
  }

  const { data: membership } = await supabase
    .from("workspace_members")
    .select("workspace_id, role")
    .eq("user_id", user.id)
    .order("created_at")
    .limit(1)
    .maybeSingle();

  const workspaceId = membership?.workspace_id ?? null;

  const [{ data: domains }, { data: limits }] = workspaceId
    ? await Promise.all([
        supabase
          .from("domains")
          .select("id, name")
          .eq("workspace_id", workspaceId)
          .order("name"),
        supabase
          .from("plan_limits")
          .select("scans_used, scans_per_month")
          .eq("workspace_id", workspaceId)
          .maybeSingle(),
      ])
    : [{ data: [] }, { data: null }];

  const domainOptions = (domains ?? []).map((domain) => ({
    id: domain.id as string,
    name: domain.name as string,
  }));
  const email = user.email ?? "GitHub user";
  const scansUsed = (limits?.scans_used as number | undefined) ?? 0;
  const scansLimit = (limits?.scans_per_month as number | undefined) ?? 5;

  return (
    <div className="min-h-dvh">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-surface-2 focus:px-4 focus:py-2 focus:text-text"
      >
        Skip to content
      </a>

      <aside className="fixed inset-y-0 left-0 z-30 hidden w-[264px] flex-col border-r border-border bg-bg p-6 lg:flex">
        <p className="font-display text-xl font-bold tracking-tight text-text">Mirsad</p>
        <div className="mt-6 flex-1">
          <SidebarContent
            email={email}
            domains={domainOptions}
            scansUsed={scansUsed}
            scansLimit={scansLimit}
          />
        </div>
      </aside>

      <div className="lg:pl-[264px]">
        <div className="mx-auto flex max-w-[1440px] flex-col gap-6 px-6 py-6 lg:px-8">
          <div className="flex items-center gap-3 lg:hidden">
            <MobileDrawer>
              <SidebarContent
                email={email}
                domains={domainOptions}
                scansUsed={scansUsed}
                scansLimit={scansLimit}
              />
            </MobileDrawer>
            <p className="font-display text-lg font-bold text-text">Mirsad</p>
            {domainOptions.length > 0 ? (
              <div className="ml-auto">
                <DomainSelector domains={domainOptions} compact />
              </div>
            ) : null}
          </div>

          <main id="main">{children}</main>
        </div>
      </div>
    </div>
  );
}
