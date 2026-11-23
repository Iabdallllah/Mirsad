import { ShieldAlert } from "lucide-react";
import { PlaceholderPage } from "@/components/ui/placeholder-page";

export const metadata = { title: "Issues" };

export default function IssuesPage() {
  return (
    <PlaceholderPage
      title="Issues"
      subtitle="Confirmed findings and informational signals, with sanitized evidence."
      phase="Phase 1 (core scan engine) and Phase 3 (web product)"
      icon={ShieldAlert}
      emptyTitle="No issues yet"
      emptyDescription="Issue lists, severity filters, lifecycle steppers, and sanitized PoC evidence arrive with the scan engine. A completed scan always includes a Coverage Receipt."
      testId="issues-empty"
    />
  );
}
