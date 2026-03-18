/**
 * Templates page — premium tab-based switcher for 3 Genie Space embed style demos.
 */

import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { motion, AnimatePresence } from "motion/react";
import { MessageSquare, MessageCircle, LayoutDashboard, Command, PanelLeftClose } from "lucide-react";
import { SimpleChatDemo } from "@/components/apx/template-testing/SimpleChatDemo";
import { FloatingWidgetDemo } from "@/components/apx/template-testing/FloatingWidgetDemo";
import { DashboardChatDemo } from "@/components/apx/template-testing/DashboardChatDemo";
import { CommandPaletteDemo } from "@/components/apx/template-testing/CommandPaletteDemo";
import { QueryWorkspaceDemo } from "@/components/apx/template-testing/QueryWorkspaceDemo";

export const Route = createFileRoute("/_sidebar/templates")({
  component: TemplatesPage,
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
  const [activeTab, setActiveTab] = useState<string>("simple");
  const activeTabObj = TABS.find((t) => t.id === activeTab)!;

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Tab bar */}
      <div className="flex gap-1 border-b px-6 pt-4 shrink-0">
        {TABS.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
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
                <span>{tab.label}</span>
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
    </div>
  );
}
