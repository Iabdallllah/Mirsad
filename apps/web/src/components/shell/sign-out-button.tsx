"use client";

import { useRouter } from "next/navigation";
import { LogOut } from "lucide-react";
import { createClient } from "@/lib/supabase/client";

export function SignOutButton() {
  const router = useRouter();

  async function signOut() {
    const supabase = createClient();
    await supabase.auth.signOut();
    // Device-token removal happens in the API on global sign-out (plan.md §9.1).
    router.push("/sign-in");
    router.refresh();
  }

  return (
    <button
      type="button"
      onClick={signOut}
      className="flex min-h-11 w-full items-center gap-3 rounded-md px-3 text-sm text-text-muted hover:bg-surface-1 hover:text-text"
    >
      <LogOut aria-hidden="true" className="size-4" />
      Sign out
    </button>
  );
}
