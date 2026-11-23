import { Globe } from "lucide-react";
import { PlaceholderPage } from "@/components/ui/placeholder-page";

export const metadata = { title: "Add domain" };

export default function NewDomainPage() {
  return (
    <PlaceholderPage
      title="Add domain"
      subtitle="Register a staging or production domain and verify ownership."
      phase="Phase 3 (web product)"
      icon={Globe}
      emptyTitle="Domain onboarding is not wired yet"
      emptyDescription="Domain creation, DNS TXT or /.well-known/verification, the rules-of-engagement consent gate, and scan quotas land together in Phase 3."
      cta={{ href: "/domains", label: "Back to domains" }}
      testId="add-domain-form"
    />
  );
}
