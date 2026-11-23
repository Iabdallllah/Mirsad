import { Globe } from "lucide-react";
import { PlaceholderPage } from "@/components/ui/placeholder-page";

type DomainDetailProps = {
  params: Promise<{ domainId: string }>;
};

export const metadata = { title: "Domain" };

export default async function DomainDetailPage({ params }: DomainDetailProps) {
  const { domainId } = await params;
  return (
    <PlaceholderPage
      title="Domain detail"
      subtitle={`Control room for domain ${domainId}.`}
      phase="Phase 3 (web product)"
      icon={Globe}
      emptyTitle="Domain detail is not wired yet"
      emptyDescription="Overview, scans, issues, auth config, repo connection, and the typed-confirmation danger zone arrive in Phase 3."
      cta={{ href: "/domains", label: "Back to domains" }}
      testId="domain-detail"
    />
  );
}
