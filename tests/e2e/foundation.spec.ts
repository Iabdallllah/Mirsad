import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { createConfirmedUser, injectSession, mintSession } from "./helpers";

/**
 * E2E-01 subset (sign-in) + Phase 0 exit criteria: GitHub-only auth, session,
 * workspace bootstrap, empty dashboard, accessibility. OAuth is "mocked" via a
 * real local Supabase session (plan.md §13.4; no external GitHub credentials).
 */

test("sign-in shows GitHub as the only sign-in method with no violations", async ({ page }) => {
  await page.goto("/sign-in");

  await expect(page.getByRole("heading", { name: "Sign in to Mirsad" })).toBeVisible();
  await expect(page.getByTestId("oauth-github")).toBeVisible();
  await expect(page.locator('input[type="password"]')).toHaveCount(0);
  await expect(page.locator('input[type="email"]')).toHaveCount(0);

  const results = await new AxeBuilder({ page }).analyze();
  expect(
    results.violations.filter((v) => v.impact === "serious" || v.impact === "critical"),
  ).toEqual([]);
});

test("unauthenticated deep links redirect to sign-in and preserve the target", async ({ page }) => {
  await page.goto("/pr-reviews/abc");

  await expect(page).toHaveURL(/\/sign-in\?next=%2Fpr-reviews%2Fabc/);
  await expect(page.getByTestId("oauth-github")).toBeVisible();
});

test("open-redirect next values are sanitized", async ({ page }) => {
  await page.goto("/sign-in?next=https%3A%2F%2Fevil.example%2Fsteal");

  // Capture the authorize request the SDK builds instead of following it to
  // the provider: the sanitized callback must be /dashboard, never evil.example.
  const authorizeRequest = page.waitForRequest((request) =>
    request.url().includes("/auth/v1/authorize"),
  );
  await page.getByTestId("oauth-github").click();
  const url = new URL((await authorizeRequest).url());
  const redirectTo = url.searchParams.get("redirect_to") ?? "";

  expect(url.hostname).toBe("127.0.0.1");
  expect(redirectTo).toBe("http://127.0.0.1:3000/auth/callback?next=%2Fdashboard");
  expect(redirectTo).not.toContain("evil.example");
});

test("authenticated owner reaches the dashboard with beta workspace bootstrap", async ({ page }) => {
  const username = `e2e-${Math.random().toString(36).slice(2, 10)}`;
  const email = await createConfirmedUser(username);
  const session = await mintSession(email);
  await injectSession(page, session);

  await page.goto("/dashboard");

  await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
  await expect(page.getByTestId("dashboard-empty")).toBeVisible();
  await expect(page.getByTestId("add-domain")).toBeVisible();
  await expect(page.getByTestId("quota-meter")).toBeVisible();
  // Honest empty state: no invented score or "secure" claim.
  await expect(page.getByText(/100%\s*secure|hacker-proof/i)).toHaveCount(0);

  const results = await new AxeBuilder({ page }).analyze();
  expect(
    results.violations.filter((v) => v.impact === "serious" || v.impact === "critical"),
  ).toEqual([]);

  // Bootstrap created the workspace + plan limits in the database.
  const { execSync } = await import("node:child_process");
  const { resolve } = await import("node:path");
  const { DATABASE_URL } = process.env;
  test.skip(!DATABASE_URL, "DATABASE_URL not set for bootstrap assertion");
  const script = resolve(process.cwd(), "tests/e2e/scripts/check-bootstrap.mjs");

  const output = execSync(`node "${script}" "${session.user.id}"`, {
    encoding: "utf8",
    env: { ...process.env, NO_COLOR: "1", FORCE_COLOR: "0" },
  });
  // pg can colorize stdout when a TTY is detected; strip ANSI before parsing.
  const count = output.replace(/\u001b\[[0-9;]*m/g, "").trim();
  expect(count).toBe("1");
});

test("authenticated route sweep has no serious/critical axe violations", async ({ page }) => {
  const email = await createConfirmedUser(`e2e-${Math.random().toString(36).slice(2, 10)}`);
  const session = await mintSession(email);
  await injectSession(page, session);

  const routes = [
    "/dashboard",
    "/domains",
    "/domains/new",
    "/domains/sample-domain",
    "/pentests",
    "/pentests/sample-scan",
    "/issues",
    "/issues/sample-issue",
    "/pr-reviews",
    "/pr-reviews/sample-patch",
    "/settings",
  ];

  for (const route of routes) {
    await page.goto(route);
    await expect(page.locator("main"), route).toBeVisible();
    const results = await new AxeBuilder({ page }).analyze();
    const blocking = results.violations.filter(
      (violation) => violation.impact === "serious" || violation.impact === "critical",
    );
    expect(blocking, `axe violations on ${route}`).toEqual([]);
  }
});

test("dashboard has no horizontal page scroll at 375px", async ({ page }) => {
  const email = await createConfirmedUser(`e2e-${Math.random().toString(36).slice(2, 10)}`);
  const session = await mintSession(email);
  await injectSession(page, session);

  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/dashboard");
  await expect(page.getByTestId("dashboard-empty")).toBeVisible();

  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - window.innerWidth,
  );
  expect(overflow).toBeLessThanOrEqual(0);
});

test("authenticated users are redirected away from sign-in", async ({ page }) => {
  const email = await createConfirmedUser(`e2e-${Math.random().toString(36).slice(2, 10)}`);
  const session = await mintSession(email);
  await injectSession(page, session);

  await page.goto("/sign-in");
  await expect(page).toHaveURL(/\/dashboard$/);
});

test("public legal pages are readable while signed out", async ({ page }) => {
  await page.goto("/privacy");
  await expect(page.getByRole("heading", { name: "Privacy Policy" })).toBeVisible();
  await page.goto("/terms");
  await expect(page.getByRole("heading", { name: "Terms of Service" })).toBeVisible();
});
