import { Suspense } from "react";
import { FeedingPanel } from "@/components/feeding-panel";

export const dynamic = "force-dynamic";

export default function FeedingPage() {
  return (
    <Suspense fallback={null}>
      <FeedingPanel />
    </Suspense>
  );
}
