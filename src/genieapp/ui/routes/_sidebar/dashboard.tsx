/**
 * Dashboard page — renders pre-computed analytics for a space.
 */

import { createFileRoute, useSearch } from "@tanstack/react-router";
import { useSpaceConfig, useSpaceDashboard } from "@/lib/api";
import { DashboardView } from "@/components/apx/DashboardView";
import { Skeleton } from "@/components/ui/skeleton";
import { BarChart3 } from "lucide-react";

interface DashboardSearch {
  spaceId?: string;
}

export const Route = createFileRoute("/_sidebar/dashboard")({
  component: DashboardPage,
  validateSearch: (search: Record<string, unknown>): DashboardSearch => ({
    spaceId: typeof search.spaceId === "string" ? search.spaceId : undefined,
  }),
});

function DashboardPage() {
  const { spaceId } = useSearch({ from: "/_sidebar/dashboard" });
  const { data: config, isLoading: configLoading } = useSpaceConfig(spaceId);
  const { data: dashboard, isLoading: dashLoading } = useSpaceDashboard(spaceId);

  if (configLoading || dashLoading) {
    // Skeleton mirroring the dashboard grid: KPI row + two chart panels.
    return (
      <div className="p-6 space-y-4">
        <Skeleton className="h-7 w-56" />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={`kpi-${i}`} className="h-24 rounded-xl" />
          ))}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Skeleton className="h-72 rounded-xl" />
          <Skeleton className="h-72 rounded-xl" />
        </div>
      </div>
    );
  }

  if (!config || !spaceId) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-3 text-muted-foreground">
        <BarChart3 className="h-10 w-10" />
        <p className="text-sm">Select a space to view its dashboard.</p>
      </div>
    );
  }

  if (!dashboard?.available || !dashboard.panels.length) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-3 text-muted-foreground">
        <BarChart3 className="h-10 w-10" />
        <p className="text-sm">No dashboard available for this space.</p>
        <p className="text-xs">Dashboards are auto-generated for pipeline-created spaces.</p>
      </div>
    );
  }

  return (
    <DashboardView
      panels={dashboard.panels}
      config={config}
      spaceId={spaceId}
    />
  );
}
