/**
 * Pure route-guard logic (unit-tested independently of Next/Supabase).
 *
 * Public: /sign-in, /auth/*. Everything else requires a session.
 * Unauthenticated deep links are preserved as ?next= (design.md §4.3).
 */

export type RouteDecision =
  | { action: "allow" }
  | { action: "redirect"; pathname: string; next?: string };

const PUBLIC_PREFIXES = ["/auth", "/terms", "/privacy"] as const;

export function isPublicPath(pathname: string): boolean {
  if (pathname === "/sign-in") return true;
  return PUBLIC_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
  );
}

export function decideRoute(input: {
  pathname: string;
  authenticated: boolean;
}): RouteDecision {
  const { pathname, authenticated } = input;

  if (authenticated && pathname === "/sign-in") {
    return { action: "redirect", pathname: "/dashboard" };
  }
  if (!authenticated && isPublicPath(pathname)) {
    return { action: "allow" };
  }
  if (!authenticated) {
    return { action: "redirect", pathname: "/sign-in", next: pathname };
  }
  return { action: "allow" };
}

/**
 * Sanitize a post-auth redirect target: same-origin absolute paths only.
 * Prevents open-redirect abuse of ?next= (e.g. //evil.example, https://…).
 */
export function safeNextPath(next: string | null | undefined): string {
  if (!next) return "/dashboard";
  if (!next.startsWith("/") || next.startsWith("//") || next.startsWith("/\\")) {
    return "/dashboard";
  }
  if (next.startsWith("/sign-in") || next.startsWith("/auth")) return "/dashboard";
  return next;
}
