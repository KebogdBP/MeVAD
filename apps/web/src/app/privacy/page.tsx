import { InfoPageView } from "@/components/info-page";
import { createInfoMetadata } from "@/lib/info-metadata";
import { infoPageMap } from "@/lib/info-pages";

const page = infoPageMap.get("privacy")!;

export const metadata = createInfoMetadata(page);

export default function PrivacyPage() {
  return <InfoPageView page={page} />;
}
