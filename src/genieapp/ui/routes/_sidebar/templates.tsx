/**
 * Templates page — tab-based switcher for 3 Genie Space embed style demos.
 */

import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { FloatingWidgetDemo } from "@/components/apx/template-testing/FloatingWidgetDemo";
import { DashboardChatDemo } from "@/components/apx/template-testing/DashboardChatDemo";
import { CommandPaletteDemo } from "@/components/apx/template-testing/CommandPaletteDemo";

export const Route = createFileRoute("/_sidebar/templates")({
  component: TemplatesPage,
});

const TABS = [
  { id: "widget", label: "Floating Widget", component: FloatingWidgetDemo },
  { id: "dashboard", label: "Dashboard + Chat", component: DashboardChatDemo },
  { id: "command", label: "Command Palette", component: CommandPaletteDemo },
] as const;

function TemplatesPage() {
  const [activeTab, setActiveTab] = useState<string>("widget");
  const ActiveComponent = TABS.find((t) => t.id === activeTab)!.component;

  return (
    <div className="flex flex-col h-full p-6 gap-4 overflow-hidden">
      <div>
        <h1 className="text-xl font-bold">Template Demos</h1>
        <p className="text-sm text-muted-foreground">
          Visual mockups of Genie Space embed styles with hardcoded Starbucks data.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors cursor-pointer ${
              activeTab === tab.id
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto relative">
        <ActiveComponent />
      </div>
    </div>
  );
}
