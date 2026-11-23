import { NextResponse, type NextRequest } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { safeNextPath } from "@/lib/routing";

/**
 * GitHub OAuth callback: exchange the code for a Supabase session, then
 * redirect to the sanitized `next` path. Errors go back to /sign-in with the
 * generic message (never internal details — design.md §6.1).
 */
export async function GET(request: NextRequest) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get("code");
  const next = safeNextPath(searchParams.get("next"));

  if (!code) {
    return NextResponse.redirect(`${origin}/sign-in?error=oauth`);
  }

  const supabase = await createClient();
  const { error } = await supabase.auth.exchangeCodeForSession(code);
  if (error) {
    return NextResponse.redirect(`${origin}/sign-in?error=oauth`);
  }

  return NextResponse.redirect(`${origin}${next}`);
}
