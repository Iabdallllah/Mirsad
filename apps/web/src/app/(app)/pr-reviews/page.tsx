import { GitPullRequest } from "lucide-react";
import { PlaceholderPage } from "@/components/ui/placeholder-page";

export const metadata = { title: "PR Reviews" };

export default function PrReviewsPage() {
  return (
    <PlaceholderPage
      title="PR Reviews"
      subtitle="A status mirror for Mirsad-authored pull requests."
      phase="Phase 2 (Blue + GitHub loop)"
      icon={GitPullRequest}
      emptyTitle="No pull requests yet"
      emptyDescription="Blue-agent PRs, CI status, merge and deploy states, and re-verification results arrive with the GitHub loop. Review and merge always happen on GitHub — Mirsad never auto-merges."
      testId="pr-reviews-empty"
    />
  );
}
