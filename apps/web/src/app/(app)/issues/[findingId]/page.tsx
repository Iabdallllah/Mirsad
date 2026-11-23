import { ShieldAlert } from "lucide-react";
import { PlaceholderPage } from "@/components/ui/placeholder-page";

type IssueDetailProps = {
  params: Promise<{ findingId: string }>;
};

export const metadata = { title: "Issue" };

export default async function IssueDetailPage({ params }: IssueDetailProps) {
  const { findingId } = await params;
  return (
    <PlaceholderPage
      title="Issue detail"
      subtitle={`Evidence and lifecycle for issue ${findingId}.`}
      phase="Phase 1 (core scan engine) and Phase 3 (web product)"
      icon={ShieldAlert}
      emptyTitle="Issue detail is not wired yet"
      emptyDescription="Lifecycle stepper, sanitized HTTP, patch diff, verification history, and terminal triage actions arrive with the scan engine."
      cta={{ href: "/issues", label: "Back to issues" }}
      testId="issue-detail"
    />
  );
}
