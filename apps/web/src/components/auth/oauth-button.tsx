"use client";

import { useState } from "react";
import { Loader2 } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { safeNextPath } from "@/lib/routing";
import { Button } from "@/components/ui/button";
import { GitHubIcon } from "@/components/ui/github-icon";

export function OAuthButton() {
  const searchParams = useSearchParams();
  const next = safeNextPath(searchParams.get("next"));
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function signIn() {
    setLoading(true);
    setError(null);
    const supabase = createClient();
    const { error: oauthError } = await supabase.auth.signInWithOAuth({
      provider: "github",
      options: {
        redirectTo: `${window.location.origin}/auth/callback?next=${encodeURIComponent(next)}`,
      },
    });
    if (oauthError) {
      setLoading(false);
      setError("GitHub sign-in was cancelled or failed. Please try again.");
    }
    // On success the browser is redirected to GitHub.
  }

  return (
    <div>
      <Button
        type="button"
        className="w-full"
        onClick={signIn}
        disabled={loading}
        aria-busy={loading}
        data-testid="oauth-github"
      >
        {loading ? (
          <>
            <Loader2 aria-hidden="true" className="size-4 animate-spin" />
            Redirecting to GitHub…
          </>
        ) : (
          <>
            <GitHubIcon className="size-4" />
            Continue with GitHub
          </>
        )}
      </Button>
      {error ? (
        <p role="alert" className="mt-3 text-sm text-critical">
          {error}
        </p>
      ) : null}
    </div>
  );
}
