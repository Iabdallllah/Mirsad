import { Settings } from "lucide-react";
import { PlaceholderPage } from "@/components/ui/placeholder-page";

export const metadata = { title: "Settings" };

export default function SettingsPage() {
  return (
    <PlaceholderPage
      title="Settings"
      subtitle="Profile, GitHub, notifications, workspace, and the danger zone."
      phase="Phase 3 (web product)"
      icon={Settings}
      emptyTitle="Settings are not wired yet"
      emptyDescription="Notification toggles, GitHub disconnect, audit retention notice, and typed-confirmation deletion arrive in Phase 3 with server-side authorization."
      testId="settings-empty"
    />
  );
}
