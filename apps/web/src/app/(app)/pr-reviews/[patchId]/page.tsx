import { GitPullRequest } from "lucide-react";
import { PlaceholderPage } from "@/components/ui/placeholder-page";

type PrDetailProps = {
  params: Promise<{ patchId: string }>;
};

export const metadata = { title: "Pull request" };

export default async function PrReviewDetailPage({ params }: PrDetailProps) {
  const { patchId } = await params;
  return (
    <PlaceholderPage
      title="PR review"
      subtitle={`Status and diff for patch ${patchId}.`}
      phase="Phase 2 (Blue + GitHub loop)"
      icon={GitPullRequest}
      emptyTitle="PR detail is not wired yet"
      emptyDescription="Diff viewer, CI checks, re-verification status, and regenerate-fix actions arrive with the GitHub loop."
      cta={{ href: "/pr-reviews", label: "Back to PR reviews" }}
      testId="pr-detail"
    />
  );
}
