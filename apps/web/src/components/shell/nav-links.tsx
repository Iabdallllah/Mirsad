"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Globe,
  Radar,
  ShieldAlert,
  GitPullRequest,
  Settings,
} from "lucide-react";

export const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/domains", label: "Domains", icon: Globe },
  { href: "/pentests", label: "Pentests", icon: Radar },
  { href: "/issues", label: "Issues", icon: ShieldAlert },
  { href: "/pr-reviews", label: "PR Reviews", icon: GitPullRequest },
  { href: "/settings", label: "Settings", icon: Settings },
] as const;

export function NavLinks({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();

  return (
    <nav aria-label="Primary" className="flex flex-col gap-1">
      {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
        const active = pathname === href || pathname.startsWith(`${href}/`);
        return (
          <Link
            key={href}
            href={href}
            onClick={onNavigate}
            aria-current={active ? "page" : undefined}
            className={`flex min-h-11 items-center gap-3 rounded-md px-3 text-sm transition-colors ${
              active
                ? "border-l-2 border-accent bg-surface-2 font-medium text-text"
                : "border-l-2 border-transparent text-text-muted hover:bg-surface-1 hover:text-text"
            }`}
          >
            <Icon aria-hidden="true" className="size-4" />
            {label}
          </Link>
        );
      })}
    </nav>
  );
}
