/**
 * Sidebar layout — resizable sidebar with nav, inline table schema, conversation history, and theme toggle.
 */

import { useState, useCallback, useRef, useEffect } from "react";
import { createFileRoute, Outlet, Link } from "@tanstack/react-router";
import { useAppConfig, useTables, useConversations } from "@/lib/api";
import { useTheme } from "@/components/apx/theme-provider";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { TableDetailPanel } from "@/components/apx/TableDetailPanel";
import {
  Home,
  MessageSquare,
  Database,
  ChevronDown,
  ChevronRight,
  Table2,
  Sun,
  Moon,
  History,
} from "lucide-react";

export const Route = createFileRoute("/_sidebar")({
  component: SidebarLayout,
});

const MIN_WIDTH = 200;
const MAX_WIDTH = 480;
const DEFAULT_WIDTH = 260;

function SidebarLayout() {
  const { data: config } = useAppConfig();
  const { data: tables } = useTables();
  const { data: conversations } = useConversations();
  const [expandedTable, setExpandedTable] = useState<string | null>(null);
  const [tablesOpen, setTablesOpen] = useState(true);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [sidebarWidth, setSidebarWidth] = useState(DEFAULT_WIDTH);
  const isResizing = useRef(false);
  const { theme, setTheme } = useTheme();

  const branding = config?.branding;

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    isResizing.current = true;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  }, []);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizing.current) return;
      const newWidth = Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, e.clientX));
      setSidebarWidth(newWidth);
    };
    const handleMouseUp = () => {
      isResizing.current = false;
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };
    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);
    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };
  }, []);

  const toggleTable = (tableName: string) => {
    setExpandedTable(expandedTable === tableName ? null : tableName);
  };

  const isDark = theme === "dark" || (theme === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches);

  return (
    <div className="flex h-screen">
      {/* Sidebar */}
      <aside
        className="border-r bg-sidebar flex flex-col shrink-0 relative"
        style={{ width: sidebarWidth }}
      >
        {/* Logo / header */}
        <div className="p-4 flex items-center gap-3">
          {branding?.logo_path && (
            <img
              src={branding.logo_path}
              alt={branding.company_name}
              className="h-8 w-auto"
            />
          )}
          <span className="font-semibold text-sm truncate">
            {branding?.company_name || "GenieApp"}
          </span>
        </div>

        <Separator />

        {/* Nav links */}
        <nav className="p-2 space-y-1">
          <Link to="/">
            <Button variant="ghost" className="w-full justify-start gap-2">
              <Home className="h-4 w-4 text-primary" />
              Home
            </Button>
          </Link>
          <Link to="/chat">
            <Button variant="ghost" className="w-full justify-start gap-2">
              <MessageSquare className="h-4 w-4 text-primary" />
              Chat
            </Button>
          </Link>
        </nav>

        <Separator />

        {/* Scrollable content: Tables + History */}
        <ScrollArea className="flex-1">
          <div className="p-2 space-y-1">
            {/* Table browser */}
            <Collapsible open={tablesOpen} onOpenChange={setTablesOpen}>
              <CollapsibleTrigger asChild>
                <Button
                  variant="ghost"
                  className="w-full justify-between gap-2"
                >
                  <span className="flex items-center gap-2">
                    <Database className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                    Tables
                  </span>
                  <ChevronDown
                    className={`h-4 w-4 transition-transform ${tablesOpen ? "" : "-rotate-90"}`}
                  />
                </Button>
              </CollapsibleTrigger>
              <CollapsibleContent className="space-y-0.5 mt-1">
                {tables?.map((table) => (
                  <div key={table.full_name}>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="w-full justify-start gap-2 pl-6 text-xs font-mono"
                      onClick={() => toggleTable(table.table_name)}
                    >
                      {expandedTable === table.table_name ? (
                        <ChevronDown className="h-3 w-3 shrink-0" />
                      ) : (
                        <ChevronRight className="h-3 w-3 shrink-0" />
                      )}
                      <Table2 className="h-3 w-3 shrink-0 text-emerald-500 dark:text-emerald-500" />
                      <span className="truncate">{table.table_name}</span>
                    </Button>
                    {expandedTable === table.table_name && (
                      <div className="pl-10 pr-2 pb-2">
                        <TableDetailPanel tableName={table.table_name} />
                      </div>
                    )}
                  </div>
                ))}
              </CollapsibleContent>
            </Collapsible>

            {/* Conversation history */}
            {conversations && conversations.length > 0 && (
              <Collapsible open={historyOpen} onOpenChange={setHistoryOpen}>
                <CollapsibleTrigger asChild>
                  <Button
                    variant="ghost"
                    className="w-full justify-between gap-2"
                  >
                    <span className="flex items-center gap-2">
                      <History className="h-4 w-4 text-violet-600 dark:text-violet-400" />
                      History
                    </span>
                    <ChevronDown
                      className={`h-4 w-4 transition-transform ${historyOpen ? "" : "-rotate-90"}`}
                    />
                  </Button>
                </CollapsibleTrigger>
                <CollapsibleContent className="space-y-0.5 mt-1">
                  {conversations.map((conv) => (
                    <Link
                      key={conv.conversation_id}
                      to="/chat"
                      search={{ conversationId: conv.conversation_id }}
                    >
                      <Button
                        variant="ghost"
                        size="sm"
                        className="w-full justify-start gap-2 pl-6 text-xs"
                      >
                        <MessageSquare className="h-3 w-3 shrink-0" />
                        <span className="truncate flex-1 text-left">
                          {conv.first_question || "Conversation"}
                        </span>
                        <Badge variant="secondary" className="text-[10px] px-1 py-0 h-4 shrink-0">
                          {conv.message_count}
                        </Badge>
                      </Button>
                    </Link>
                  ))}
                </CollapsibleContent>
              </Collapsible>
            )}
          </div>
        </ScrollArea>

        {/* Theme toggle */}
        <Separator />
        <div className="p-2">
          <Button
            variant="ghost"
            size="sm"
            className="w-full justify-start gap-2 text-xs"
            onClick={() => setTheme(isDark ? "light" : "dark")}
          >
            {isDark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            {isDark ? "Light Mode" : "Dark Mode"}
          </Button>
        </div>

        {/* Resize handle */}
        <div
          className="absolute top-0 right-0 w-1 h-full cursor-col-resize hover:bg-primary/20 active:bg-primary/40 transition-colors"
          onMouseDown={handleMouseDown}
        />
      </aside>

      {/* Main content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        <Outlet />
      </main>
    </div>
  );
}
