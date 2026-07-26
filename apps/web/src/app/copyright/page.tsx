import { InfoPageView } from "@/components/info-page";
import { createInfoMetadata } from "@/lib/info-metadata";
import { infoPageMap } from "@/lib/info-pages";

const page = infoPageMap.get("copyright")!;

export const metadata = createInfoMetadata(page);

export default function CopyrightPage() {
  return <InfoPageView page={page} />;
}
