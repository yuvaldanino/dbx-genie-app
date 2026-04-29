/**
 * Sandbox shell — scenario picker + theme toggle.
 * Renders whichever component scenario is selected.
 */

import { useState } from "react";
import { useTheme } from "@/components/apx/theme-provider";
import { Sun, Moon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { scenarios } from "./test-scenarios";

export function SandboxApp() {
  const [activeScenario, setActiveScenario] = useState(0);
  const { theme, setTheme } = useTheme();
  const scenario = scenarios[activeScenario];

  return (
    <div className="h-screen flex flex-col bg-background text-foreground">
      {/* Toolbar */}
      <div className="border-b px-4 py-3 flex items-center gap-4 bg-card">
        <span className="font-semibold text-sm tracking-tight">
          Component Sandbox
        </span>
        <select
          className="border rounded-md px-3 py-1.5 text-sm bg-background cursor-pointer"
          value={activeScenario}
          onChange={(e) => setActiveScenario(Number(e.target.value))}
        >
          {scenarios.map((s, i) => (
            <option key={i} value={i}>
              {s.name}
            </option>
          ))}
        </select>
        <span className="text-xs text-muted-foreground">{scenario.description}</span>
        <div className="ml-auto">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          >
            {theme === "dark" ? (
              <Sun className="h-4 w-4" />
            ) : (
              <Moon className="h-4 w-4" />
            )}
          </Button>
        </div>
      </div>

      {/* Render area */}
      <div className="flex-1 overflow-auto">
        {scenario.render()}
      </div>
    </div>
  );
}
