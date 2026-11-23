/**
 * Bootstrap verification for E2E: asserts the auth trigger provisioned
 * plan_limits for the user's workspace. Usage: node scripts/check-bootstrap.mjs <user-id>
 * Requires DATABASE_URL in the environment (local Supabase only).
 */
import { Client } from "pg";

const userId = process.argv[2];
if (!userId) {
  console.error("usage: check-bootstrap.mjs <user-id>");
  process.exit(2);
}

const client = new Client({ connectionString: process.env.DATABASE_URL });
await client.connect();
try {
  const result = await client.query(
    `select count(*)::int as count
     from public.plan_limits pl
     join public.workspaces w on w.id = pl.workspace_id
     where w.owner_user_id = $1::uuid`,
    [userId],
  );
  console.log(result.rows[0].count);
} finally {
  await client.end();
}
