/**
 * TemplateRenderer — renders the correct template component for a space,
 * passing real data from React Query hooks and wiring chat to useChatFlow.
 *
 * For now, all templates fall back to the existing chat.tsx UI since
 * template components are still self-contained with mock data.
 * This component provides the mapping and will be the integration point
 * when templates are refactored to accept props.
 */

import { lazy, Suspense } from "react";
import { Loader2 } from "lucide-react";

const SimpleChatDemo = lazy(() =>
  import("@/components/apx/template-testing/SimpleChatDemo").then((m) => ({
    default: m.SimpleChatDemo,
  })),
);
const FloatingWidgetDemo = lazy(() =>
  import("@/components/apx/template-testing/FloatingWidgetDemo").then((m) => ({
    default: m.FloatingWidgetDemo,
  })),
);
const DashboardChatDemo = lazy(() =>
  import("@/components/apx/template-testing/DashboardChatDemo").then((m) => ({
    default: m.DashboardChatDemo,
  })),
);
const CommandPaletteDemo = lazy(() =>
  import("@/components/apx/template-testing/CommandPaletteDemo").then((m) => ({
    default: m.CommandPaletteDemo,
  })),
);
const QueryWorkspaceDemo = lazy(() =>
  import("@/components/apx/template-testing/QueryWorkspaceDemo").then((m) => ({
    default: m.QueryWorkspaceDemo,
  })),
);

const TEMPLATE_MAP: Record<string, React.LazyExoticComponent<React.ComponentType>> = {
  simple: SimpleChatDemo,
  widget: FloatingWidgetDemo,
  dashboard: DashboardChatDemo,
  command: CommandPaletteDemo,
  workspace: QueryWorkspaceDemo,
};

interface TemplateRendererProps {
  templateId: string;
}

export function TemplateRenderer({ templateId }: TemplateRendererProps) {
  const Component = TEMPLATE_MAP[templateId];

  if (!Component) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground">
        Unknown template: {templateId}
      </div>
    );
  }

  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center h-full">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      }
    >
      <Component />
    </Suspense>
  );
}
