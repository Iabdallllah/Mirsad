import { defineConfig, devices } from "@playwright/test";
import { readFileSync } from "node:fs";

/** Load git-ignored local test env (never committed — AGENTS.md §4). */
function loadEnvFile(path: string): Record<string, string> {
  try {
    return Object.fromEntries(
      readFileSync(path, "utf8")
        .split("\n")
        .filter((line) => line.includes("=") && !line.trimStart().startsWith("#"))
        .map((line) => {
          const index = line.indexOf("=");
          let value = line.slice(index + 1).trim();
          // `supabase status -o env` quotes values; strip surrounding quotes so
          // process.env gets a bare URL/key (quotes would break createClient).
          if (
            (value.startsWith('"') && value.endsWith('"')) ||
            (value.startsWith("'") && value.endsWith("'"))
          ) {
            value = value.slice(1, -1);
          }
          return [line.slice(0, index).trim(), value];
        }),
    );
  } catch {
    return {};
  }
}

const localEnv = loadEnvFile(".env.test");

// Make the local test env available to specs too (session minting), not just
// the web server. Values are git-ignored placeholders for the local stack.
for (const [key, value] of Object.entries(localEnv)) {
  if (value && !process.env[key]) process.env[key] = value;
}

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 45_000,
  expect: { timeout: 10_000 },
  reporter: [["list"]],
  use: {
    baseURL: "http://127.0.0.1:3000",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: "npm run dev --workspace apps/web -- --port 3000",
    url: "http://127.0.0.1:3000/sign-in",
    reuseExistingServer: true,
    timeout: 120_000,
    env: {
      ...localEnv,
      NEXT_PUBLIC_SUPABASE_URL:
        process.env.NEXT_PUBLIC_SUPABASE_URL ?? "http://127.0.0.1:54321",
    },
  },
});
