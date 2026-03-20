/**
 * Dashboard page — renders pre-computed analytics for a space.
 */

import { createFileRoute, useSearch } from "@tanstack/react-router";
import { useSpaceConfig, useSpaceDashboard } from "@/lib/api";
import { DashboardView } from "@/components/apx/DashboardView";
import { Loader2, BarChart3 } from "lucide-react";

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
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
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
