import Link from "next/link";
import { Suspense } from "react";
import { GitHubIcon } from "@/components/ui/github-icon";
import { OAuthButton } from "@/components/auth/oauth-button";

type SignInPageProps = {
  searchParams: Promise<{ error?: string }>;
};

export const metadata = { title: "Sign in" };

export default async function SignInPage({ searchParams }: SignInPageProps) {
  const { error } = await searchParams;

  return (
    <main className="flex min-h-dvh items-center justify-center px-6 py-12">
      <div className="w-full max-w-sm">
        <p className="font-display text-3xl font-bold tracking-tight text-text">Mirsad</p>
        <p className="mt-2 text-base text-text-muted">
          Continuous, evidence-based application security for your team.
        </p>

        <div className="mt-8 rounded-lg border border-border bg-surface-1 p-6">
          <h1 className="text-xl font-semibold text-text">Sign in to Mirsad</h1>
          <p className="mt-1 text-sm text-text-muted">
            Mirsad uses GitHub for authentication. No passwords are stored.
          </p>

          {error ? (
            <div
              role="alert"
              aria-live="assertive"
              className="mt-4 rounded-md border border-critical/50 bg-critical/10 px-3 py-2 text-sm text-critical"
            >
              <GitHubIcon className="mr-2 inline size-4" />
              GitHub sign-in was cancelled or failed. Please try again.
            </div>
          ) : null}

          <div className="mt-6">
            <Suspense fallback={null}>
              <OAuthButton />
            </Suspense>
          </div>
        </div>

        <p className="mt-6 text-center text-xs text-text-muted">
          By continuing you agree to the Terms and Privacy Policy.{" "}
          <Link className="text-accent underline underline-offset-4" href="/terms">
            Terms
          </Link>{" "}
          ·{" "}
          <Link className="text-accent underline underline-offset-4" href="/privacy">
            Privacy
          </Link>
        </p>
      </div>
    </main>
  );
}
