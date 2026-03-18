/**
 * Templates page — browse and select UI templates for the current space.
 * Calls PATCH /api/spaces/{spaceId}/template to persist selection.
 */

import { useState } from "react";
import { createFileRoute, useSearch } from "@tanstack/react-router";
import { motion, AnimatePresence } from "motion/react";
import {
  MessageSquare,
  MessageCircle,
  LayoutDashboard,
  Command,
  PanelLeftClose,
  Check,
} from "lucide-react";
import { SimpleChatDemo } from "@/components/apx/template-testing/SimpleChatDemo";
import { FloatingWidgetDemo } from "@/components/apx/template-testing/FloatingWidgetDemo";
import { DashboardChatDemo } from "@/components/apx/template-testing/DashboardChatDemo";
import { CommandPaletteDemo } from "@/components/apx/template-testing/CommandPaletteDemo";
import { QueryWorkspaceDemo } from "@/components/apx/template-testing/QueryWorkspaceDemo";
import { useSpaceConfig, useUpdateSpaceTemplate } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { useQueryClient } from "@tanstack/react-query";

interface TemplatesSearch {
  spaceId?: string;
}

export const Route = createFileRoute("/_sidebar/templates")({
  component: TemplatesPage,
  validateSearch: (search: Record<string, unknown>): TemplatesSearch => ({
    spaceId: typeof search.spaceId === "string" ? search.spaceId : undefined,
  }),
});

const TABS = [
  {
    id: "simple",
    label: "Simple Chat",
    desc: "Full-page conversation",
    icon: MessageSquare,
    component: SimpleChatDemo,
  },
  {
    id: "widget",
    label: "Floating Widget",
    desc: "Chat bubble overlay",
    icon: MessageCircle,
    component: FloatingWidgetDemo,
  },
  {
    id: "dashboard",
    label: "Dashboard + Chat",
    desc: "Split panel layout",
    icon: LayoutDashboard,
    component: DashboardChatDemo,
  },
  {
    id: "command",
    label: "Command Palette",
    desc: "Spotlight search",
    icon: Command,
    component: CommandPaletteDemo,
  },
  {
    id: "workspace",
    label: "Query Workspace",
    desc: "Saved queries panel",
    icon: PanelLeftClose,
    component: QueryWorkspaceDemo,
  },
] as const;

function TemplatesPage() {
  const { spaceId } = useSearch({ from: "/_sidebar/templates" });
  const { data: spaceConfig } = useSpaceConfig(spaceId);
  const updateTemplate = useUpdateSpaceTemplate();
  const queryClient = useQueryClient();

  const [activeTab, setActiveTab] = useState<string>("simple");
  const activeTabObj = TABS.find((t) => t.id === activeTab)!;

  const currentTemplateId = spaceConfig
    ? (spaceConfig as unknown as { template_id?: string }).template_id ?? "simple"
    : undefined;

  const handleSelectTemplate = (templateId: string) => {
    if (!spaceId) return;
    updateTemplate.mutate(
      { spaceId, templateId },
      {
        onSuccess: () => {
          queryClient.invalidateQueries({ queryKey: ["spaceConfig", spaceId] });
          queryClient.invalidateQueries({ queryKey: ["spaces"] });
        },
      },
    );
  };

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Tab bar */}
      <div className="flex gap-1 border-b px-6 pt-4 shrink-0">
        {TABS.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          const isSelected = currentTemplateId === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`relative flex items-center gap-2 px-4 py-3 text-sm font-medium transition-colors cursor-pointer ${
                isActive ? "text-primary" : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <Icon className="h-4 w-4" />
              <div className="flex flex-col items-start">
                <span className="flex items-center gap-1.5">
                  {tab.label}
                  {isSelected && <Check className="h-3 w-3 text-green-500" />}
                </span>
                <span className="text-[10px] font-normal text-muted-foreground">
                  {tab.desc}
                </span>
              </div>
              {isActive && (
                <motion.div
                  layoutId="tab-underline"
                  className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary"
                  transition={{ type: "spring", damping: 25, stiffness: 300 }}
                />
              )}
            </button>
          );
        })}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden relative p-4">
        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.2 }}
            className="h-full"
          >
            <activeTabObj.component />
          </motion.div>
        </AnimatePresence>
      </div>

      {/* Apply button */}
      {spaceId && activeTab !== currentTemplateId && (
        <div className="border-t bg-background p-4 flex justify-end shrink-0">
          <Button
            onClick={() => handleSelectTemplate(activeTab)}
            disabled={updateTemplate.isPending}
          >
            {updateTemplate.isPending ? "Applying..." : `Apply "${activeTabObj.label}" template`}
          </Button>
        </div>
      )}
    </div>
  );
}
