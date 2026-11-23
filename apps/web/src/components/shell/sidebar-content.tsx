import { DomainSelector } from "@/components/shell/domain-selector";
import { NavLinks } from "@/components/shell/nav-links";
import { QuotaMeter } from "@/components/shell/quota-meter";
import { SignOutButton } from "@/components/shell/sign-out-button";

type SidebarContentProps = {
  email: string;
  domains: { id: string; name: string }[];
  scansUsed: number;
  scansLimit: number;
  onNavigate?: () => void;
};

export function SidebarContent({
  email,
  domains,
  scansUsed,
  scansLimit,
  onNavigate,
}: SidebarContentProps) {
  return (
    <div className="flex h-full flex-col gap-6">
      <div>
        <DomainSelector domains={domains} onNavigate={onNavigate} />
      </div>
      <div onClick={onNavigate}>
        <NavLinks onNavigate={onNavigate} />
      </div>
      <div className="mt-auto flex flex-col gap-3">
        <QuotaMeter used={scansUsed} limit={scansLimit} />
        <div className="flex items-center gap-3 rounded-md px-1 py-2">
          <span
            aria-hidden="true"
            className="flex size-8 shrink-0 items-center justify-center rounded-full bg-secondary text-xs font-semibold uppercase text-text"
          >
            {email.slice(0, 2)}
          </span>
          <span className="min-w-0 flex-1 truncate text-xs text-text-muted" title={email}>
            {email}
          </span>
        </div>
        <SignOutButton />
      </div>
    </div>
  );
}
