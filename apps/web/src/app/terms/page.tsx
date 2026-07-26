import { InfoPageView } from "@/components/info-page";
import { createInfoMetadata } from "@/lib/info-metadata";
import { infoPageMap } from "@/lib/info-pages";

const page = infoPageMap.get("terms")!;

export const metadata = createInfoMetadata(page);

export default function TermsPage() {
  return <InfoPageView page={page} />;
}
