import { InfoPageView } from "@/components/info-page";
import { createInfoMetadata } from "@/lib/info-metadata";
import { infoPageMap } from "@/lib/info-pages";

const page = infoPageMap.get("how-it-works")!;

export const metadata = createInfoMetadata(page);

export default function HowItWorksPage() {
  return <InfoPageView page={page} />;
}
