import { Suspense } from "react";
import { FeedingPanel } from "@/components/feeding-panel";

export default function FeedingPage() {
  return (
    <Suspense fallback={null}>
      <FeedingPanel />
    </Suspense>
  );
}
