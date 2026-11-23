/**
 * E2E helpers for the local Supabase environment.
 *
 * GitHub OAuth needs external credentials, so specs mint a REAL local
 * Supabase session through the admin API (email + hashed magic link) and
 * inject it exactly as @supabase/ssr stores it:
 *  - base64url cookie (server/middleware path), encodeURIComponent-wrapped
 *  - localStorage entry (browser client path)
 * Keys come from the git-ignored .env.test; no secret is committed.
 */

export const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL ?? "http://127.0.0.1:54321";
const SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY ?? "";
const ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "";

/** sb-<first hostname segment>-auth-token (supabase-js default storage key). */
export const STORAGE_KEY = `sb-${new URL(SUPABASE_URL).hostname.split(".")[0]}-auth-token`;

type Session = {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  expires_at: number;
  token_type: string;
  user: { id: string; email?: string };
};

function headers(key: string) {
  return {
    apikey: key,
    Authorization: `Bearer ${key}`,
    "Content-Type": "application/json",
  };
}

export async function createConfirmedUser(username: string): Promise<string> {
  const email = `${username}-${Date.now()}@users.noreply.github.com`;
  const response = await fetch(`${SUPABASE_URL}/auth/v1/admin/users`, {
    method: "POST",
    headers: headers(SERVICE_ROLE_KEY),
    body: JSON.stringify({
      email,
      password: crypto.randomUUID(),
      email_confirm: true,
      user_metadata: { user_name: username, avatar_url: "https://example.com/a.png" },
    }),
  });
  if (!response.ok)
    throw new Error(`create user failed: ${response.status} ${await response.text()}`);
  return email;
}

export async function mintSession(email: string): Promise<Session> {
  const linkResponse = await fetch(`${SUPABASE_URL}/auth/v1/admin/generate_link`, {
    method: "POST",
    headers: headers(SERVICE_ROLE_KEY),
    body: JSON.stringify({ type: "magiclink", email }),
  });
  if (!linkResponse.ok) throw new Error(`generate link failed: ${linkResponse.status}`);
  const link = (await linkResponse.json()) as { hashed_token: string };

  const verifyResponse = await fetch(`${SUPABASE_URL}/auth/v1/verify`, {
    method: "POST",
    headers: headers(ANON_KEY),
    body: JSON.stringify({ type: "magiclink", token_hash: link.hashed_token }),
  });
  if (!verifyResponse.ok) throw new Error(`verify failed: ${verifyResponse.status}`);
  return (await verifyResponse.json()) as Session;
}

function sessionPayload(session: Session) {
  return {
    provider_token: null,
    provider_refresh_token: null,
    access_token: session.access_token,
    refresh_token: session.refresh_token,
    expires_in: session.expires_in,
    expires_at: session.expires_at,
    token_type: session.token_type,
    user: session.user,
  };
}

/**
 * Inject the session before any app code runs: localStorage for the browser
 * client, and the base64url cookie the server client/middleware reads.
 * @supabase/ssr writes cookie values as `base64-<base64url(JSON)>`; the
 * browser percent-encodes on its own, so no extra encodeURIComponent here.
 */
export async function injectSession(
  page: import("@playwright/test").Page,
  session: Session,
  baseURL = "http://127.0.0.1:3000",
) {
  const stored = sessionPayload(session);
  const cookieValue = `base64-${Buffer.from(JSON.stringify(stored), "utf8").toString("base64url")}`;

  await page.context().addCookies([
    {
      name: STORAGE_KEY,
      value: cookieValue,
      url: baseURL,
      httpOnly: false,
      sameSite: "Lax",
    },
  ]);

  await page.addInitScript(
    ([key, value]) => window.localStorage.setItem(key, JSON.stringify(value)),
    [STORAGE_KEY, stored] as const,
  );
}
