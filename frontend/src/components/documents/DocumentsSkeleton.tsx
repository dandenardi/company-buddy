"use client";

import { Skeleton } from "@/components/ui/Skeleleton";

export function DocumentsSkeleton() {
  return (
    <div className="space-y-2 px-4 py-3">
      {[1, 2, 3].map((item) => (
        <div
          key={item}
          className="flex items-center justify-between rounded-lg border border-border bg-card px-4 py-3"
        >
          <div className="space-y-1">
            <Skeleton className="h-4 w-40" />
            <Skeleton className="h-3 w-24" />
          </div>
          <Skeleton className="h-8 w-32" />
        </div>
      ))}
    </div>
  );
}
