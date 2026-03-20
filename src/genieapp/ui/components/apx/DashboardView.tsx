/**
 * Dashboard view — renders pre-computed chart panels in a responsive grid
 * with a floating Genie chat button.
 */

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ChartRenderer } from "./ChartRenderer";
import { GenieDrawer } from "./GenieDrawer";
import { MessageSquare } from "lucide-react";
import type { DashboardPanel, AppConfigOut } from "@/lib/api";

interface DashboardViewProps {
  panels: DashboardPanel[];
  config: AppConfigOut;
  spaceId?: string;
}

function KpiCard({ panel }: { panel: DashboardPanel }) {
  const value = panel.data[0]?.[panel.columns[0]];
  return (
    <Card className="border-accent/20">
      <CardContent className="flex flex-col items-center justify-center py-8">
        <p className="text-sm text-muted-foreground">{panel.title}</p>
        <p className="text-5xl font-bold mt-2 text-primary">
          {typeof value === "number"
            ? value.toLocaleString()
            : String(value ?? "—")}
        </p>
      </CardContent>
    </Card>
  );
}

function ChartCard({ panel }: { panel: DashboardPanel }) {
  if (!panel.columns.length || !panel.data.length) return null;

  const numericCols = panel.columns.filter((c) =>
    panel.data.slice(0, 10).some((row) => !isNaN(Number(row[c])) && row[c] !== null && row[c] !== ""),
  );

  return (
    <Card className="border-accent/20">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium">{panel.title}</CardTitle>
      </CardHeader>
      <CardContent>
        <ChartRenderer
          suggestion={{
            chart_type: panel.chart_type as "bar" | "line" | "pie" | "area",
            x_axis: panel.columns[0],
            y_axis: numericCols[0] || panel.columns[1] || panel.columns[0],
            title: "",
          }}
          data={panel.data}
          columns={panel.columns}
        />
      </CardContent>
    </Card>
  );
}

export function DashboardView({ panels, config, spaceId }: DashboardViewProps) {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const companyName = config.branding.company_name;

  return (
    <div className="relative h-full flex flex-col">
      {/* Header */}
      <div className="border-b px-6 py-4 shrink-0">
        <h1 className="text-xl font-semibold">{companyName} Dashboard</h1>
        <p className="text-sm text-muted-foreground">
          Pre-computed analytics overview
        </p>
      </div>

      {/* Panel grid */}
      <ScrollArea className="flex-1">
        <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-4">
          {panels.map((panel) =>
            panel.chart_type === "kpi" ? (
              <KpiCard key={panel.id} panel={panel} />
            ) : (
              <ChartCard key={panel.id} panel={panel} />
            ),
          )}
        </div>
      </ScrollArea>

      {/* Floating Genie button */}
      <Button
        className="fixed bottom-6 right-6 h-14 w-14 rounded-full shadow-lg z-40"
        onClick={() => setDrawerOpen(true)}
      >
        <MessageSquare className="h-6 w-6" />
      </Button>

      {/* Genie chat drawer */}
      <GenieDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        spaceId={spaceId}
        config={config}
      />
    </div>
  );
}
