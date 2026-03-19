/**
 * Query Workspace template — tabbed sidebar (Recent / Saved) with query cards,
 * right panel with results, bottom input bar.
 */

import { useState } from "react";
import { useChatFlow } from "@/lib/useChatFlow";
import { useStarredMessages, useToggleStar, useConversations } from "@/lib/api";
import { useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ChartRenderer } from "@/components/apx/ChartRenderer";
import { DataTable } from "@/components/apx/DataTable";
import {
  Send,
  Loader2,
  Code2,
  ChevronDown,
  ChevronRight,
  Inbox,
  Pin,
  PinOff,
} from "lucide-react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import type { TemplateProps } from "./types";
import type { Message } from "@/lib/useChatFlow";

/** Determine what kind of result a message has. */
function getResultType(msg: Message): "Chart" | "Table" | "Error" | "Pending" {
  if (!msg.response) return "Pending";
  if (msg.response.error) return "Error";
  if (msg.response.columns.length >= 2 && msg.response.data.length > 0) return "Chart";
  if (msg.response.columns.length > 0 && msg.response.data.length > 0) return "Table";
  return "Table";
}

/** Badge color for result type. */
function ResultBadge({ type }: { type: "Chart" | "Table" | "Error" | "Pending" }) {
  if (type === "Pending") return null;
  const colors = {
    Chart: "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300",
    Table: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300",
    Error: "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300",
  };
  return (
    <span className={`inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-medium ${colors[type]}`}>
      {type}
    </span>
  );
}

export function QueryWorkspace({ spaceId, config, initialConversationId }: TemplateProps) {
  // Auto-load most recent conversation if none specified in URL
  const { data: conversations } = useConversations(spaceId);
  const effectiveConvId =
    initialConversationId ??
    (conversations && conversations.length > 0 ? conversations[0].conversation_id : undefined);

  const { messages, setMessages, isSending, sendMessage } = useChatFlow({
    spaceId,
    initialConversationId: effectiveConvId,
  });
  const [input, setInput] = useState("");
  const [selectedIdx, setSelectedIdx] = useState<number | null>(null);
  const [savedSelectedIdx, setSavedSelectedIdx] = useState<number | null>(null);
  const [sidebarTab, setSidebarTab] = useState<"recent" | "saved">("recent");

  const { data: starredMessages = [] } = useStarredMessages(spaceId);
  const toggleStarMutation = useToggleStar();
  const queryClient = useQueryClient();

  function handleSend(question?: string) {
    const q = question || input.trim();
    if (!q) return;
    setInput("");
    sendMessage(q);
    setSelectedIdx(null);
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  function handleToggleStar(msg: Message, idx: number, e: React.MouseEvent) {
    e.stopPropagation();
    if (!msg.response?.conversation_id || !msg.response?.message_id) return;
    const newStarred = !msg.is_starred;

    // Optimistic local update — updates pin icon in Recent tab instantly
    setMessages((prev) => {
      const updated = [...prev];
      updated[idx] = { ...updated[idx], is_starred: newStarred };
      return updated;
    });

    toggleStarMutation.mutate(
      {
        convId: msg.response.conversation_id,
        msgId: msg.response.message_id,
        starred: newStarred,
      },
      {
        onSuccess: () => {
          // Refetch starred messages so Saved tab updates
          queryClient.invalidateQueries({ queryKey: ["starredMessages", spaceId] });
          queryClient.invalidateQueries({ queryKey: ["conversationMessages"] });
        },
        onError: () => {
          // Revert optimistic update on failure
          setMessages((prev) => {
            const updated = [...prev];
            updated[idx] = { ...updated[idx], is_starred: !newStarred };
            return updated;
          });
        },
      },
    );
  }

  // Selected message — pick from correct source based on active tab
  const activeIdx = selectedIdx ?? (messages.length > 0 ? messages.length - 1 : null);
  const activeMsg: Message | null = (() => {
    if (sidebarTab === "saved" && savedSelectedIdx !== null) {
      const sm = starredMessages[savedSelectedIdx];
      if (!sm) return null;
      return { question: sm.question, response: sm.response ?? undefined, is_starred: sm.is_starred };
    }
    return activeIdx !== null ? messages[activeIdx] : null;
  })();

  const savedCount = starredMessages.length;

  return (
    <div className="flex h-full overflow-hidden">
      {/* Left sidebar */}
      <div className="w-80 shrink-0 border-r flex flex-col">
        {/* Tab bar */}
        <div className="flex border-b">
          <button
            className={`flex-1 py-2.5 text-sm font-medium text-center transition-colors relative ${
              sidebarTab === "recent"
                ? "text-foreground"
                : "text-muted-foreground hover:text-foreground"
            }`}
            onClick={() => setSidebarTab("recent")}
          >
            Recent
            {sidebarTab === "recent" && (
              <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary" />
            )}
          </button>
          <button
            className={`flex-1 py-2.5 text-sm font-medium text-center transition-colors relative ${
              sidebarTab === "saved"
                ? "text-foreground"
                : "text-muted-foreground hover:text-foreground"
            }`}
            onClick={() => setSidebarTab("saved")}
          >
            Saved
            {savedCount > 0 && (
              <span className="ml-1.5 inline-flex items-center justify-center h-5 min-w-5 px-1 rounded-full bg-muted text-[10px] font-semibold">
                {savedCount}
              </span>
            )}
            {sidebarTab === "saved" && (
              <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary" />
            )}
          </button>
        </div>

        {/* Tab content */}
        <ScrollArea className="flex-1">
          {sidebarTab === "recent" ? (
            <div className="p-3 space-y-2">
              {messages.length === 0 ? (
                <div className="text-center py-12 text-muted-foreground">
                  <Inbox className="h-8 w-8 mx-auto mb-2 opacity-40" />
                  <p className="text-xs">No queries yet</p>
                  <p className="text-[10px] mt-1">Ask a question to get started</p>
                </div>
              ) : (
                messages.map((msg, i) => {
                  const isActive = activeIdx === i;
                  const resultType = getResultType(msg);
                  return (
                    <div
                      key={i}
                      className={`rounded-lg border px-3 py-2.5 cursor-pointer transition-all ${
                        isActive
                          ? "bg-amber-50 border-amber-200 dark:bg-amber-950/30 dark:border-amber-800/50 shadow-sm"
                          : "bg-card hover:bg-muted/50 border-transparent hover:border-border"
                      }`}
                      onClick={() => setSelectedIdx(i)}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <p className={`text-sm leading-snug ${isActive ? "font-medium" : ""} line-clamp-2`}>
                          {msg.question}
                        </p>
                        {msg.response && (
                          <button
                            className={`shrink-0 mt-0.5 p-0.5 rounded transition-colors ${
                              msg.is_starred
                                ? "text-primary"
                                : "text-muted-foreground/40 hover:text-muted-foreground"
                            }`}
                            onClick={(e) => handleToggleStar(msg, i, e)}
                            title={msg.is_starred ? "Unsave" : "Save"}
                          >
                            {msg.is_starred ? (
                              <PinOff className="h-3.5 w-3.5" />
                            ) : (
                              <Pin className="h-3.5 w-3.5" />
                            )}
                          </button>
                        )}
                      </div>
                      <div className="flex items-center gap-2 mt-1.5">
                        {msg.response ? (
                          <>
                            <ResultBadge type={resultType} />
                            {msg.response.row_count > 0 && (
                              <span className="text-[10px] text-muted-foreground">
                                {msg.response.row_count} rows
                              </span>
                            )}
                          </>
                        ) : (
                          <span className="text-[10px] text-muted-foreground flex items-center gap-1">
                            <Loader2 className="h-2.5 w-2.5 animate-spin" />
                            {msg.statusText || "Processing..."}
                          </span>
                        )}
                        {msg.is_starred && (
                          <Pin className="h-2.5 w-2.5 text-primary ml-auto" />
                        )}
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          ) : (
            <div className="p-3 space-y-2">
              {savedCount === 0 ? (
                <div className="text-center py-12 text-muted-foreground">
                  <Pin className="h-8 w-8 mx-auto mb-2 opacity-40" />
                  <p className="text-xs">No saved queries</p>
                  <p className="text-[10px] mt-1">Pin queries to save them here</p>
                </div>
              ) : (
                starredMessages.map((sm, i) => {
                  const resultType = sm.response
                    ? sm.response.columns.length >= 2 && sm.response.data.length > 0
                      ? "Chart"
                      : "Table"
                    : "Table";
                  const isSavedActive = savedSelectedIdx === i;
                  return (
                    <div
                      key={`saved-${i}`}
                      className={`rounded-lg border px-3 py-2.5 cursor-pointer transition-all ${
                        isSavedActive
                          ? "bg-amber-50 border-amber-200 dark:bg-amber-950/30 dark:border-amber-800/50 shadow-sm"
                          : "bg-card hover:bg-muted/50 border-transparent hover:border-border"
                      }`}
                      onClick={() => setSavedSelectedIdx(i)}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <p className={`text-sm leading-snug ${isSavedActive ? "font-medium" : ""} line-clamp-2`}>
                          {sm.question}
                        </p>
                        <button
                          className="shrink-0 mt-0.5 p-0.5 rounded transition-colors text-primary hover:text-destructive"
                          onClick={(e) => {
                            e.stopPropagation();
                            if (!sm.response?.conversation_id || !sm.response?.message_id) return;
                            // Optimistic update — sync Recent tab pin icon
                            const matchIdx = messages.findIndex(
                              (m) => m.response?.message_id === sm.response?.message_id,
                            );
                            if (matchIdx >= 0) {
                              setMessages((prev) => {
                                const updated = [...prev];
                                updated[matchIdx] = { ...updated[matchIdx], is_starred: false };
                                return updated;
                              });
                            }
                            toggleStarMutation.mutate(
                              {
                                convId: sm.response.conversation_id,
                                msgId: sm.response.message_id,
                                starred: false,
                              },
                              {
                                onSuccess: () => {
                                  if (savedSelectedIdx === i) setSavedSelectedIdx(null);
                                  else if (savedSelectedIdx !== null && savedSelectedIdx > i) setSavedSelectedIdx(savedSelectedIdx - 1);
                                  queryClient.invalidateQueries({ queryKey: ["starredMessages", spaceId] });
                                  queryClient.invalidateQueries({ queryKey: ["conversationMessages"] });
                                },
                              },
                            );
                          }}
                          title="Unpin"
                        >
                          <PinOff className="h-3.5 w-3.5" />
                        </button>
                      </div>
                      <div className="flex items-center gap-2 mt-1.5">
                        <ResultBadge type={resultType as "Chart" | "Table"} />
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          )}
        </ScrollArea>

        {/* Sample questions as starters */}
        {messages.length === 0 && sidebarTab === "recent" && config.sample_questions.length > 0 && (
          <div className="border-t p-3 space-y-1.5">
            <p className="text-[10px] text-muted-foreground font-medium uppercase tracking-wider px-1">
              Try asking
            </p>
            {config.sample_questions.slice(0, 3).map((q) => (
              <button
                key={q}
                className="w-full text-left rounded-md px-2.5 py-1.5 text-xs text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
                onClick={() => handleSend(q)}
              >
                {q}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Right panel — results + input */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Results */}
        <ScrollArea className="flex-1">
          <div className="p-6">
            {activeMsg ? (
              <QueryResult msg={activeMsg} />
            ) : (
              <div className="flex flex-col items-center justify-center min-h-[400px] text-center">
                <Inbox className="h-12 w-12 text-muted-foreground/30 mb-3" />
                <p className="text-muted-foreground">
                  Type a question below to get started
                </p>
              </div>
            )}
          </div>
        </ScrollArea>

        {/* Bottom input */}
        <div className="border-t p-4">
          <div className="flex gap-2">
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a question about your data..."
              disabled={isSending}
              className="flex-1"
            />
            <Button
              onClick={() => handleSend()}
              disabled={isSending || !input.trim()}
              size="icon"
            >
              {isSending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

/** Single query result display. */
function QueryResult({ msg }: { msg: Message }) {
  const [sqlExpanded, setSqlExpanded] = useState(false);

  if (!msg.response) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[300px]">
        <Loader2 className="h-8 w-8 animate-spin text-primary mb-3" />
        <p className="text-sm text-muted-foreground">{msg.statusText || "Processing..."}</p>
      </div>
    );
  }

  const r = msg.response;

  return (
    <div className="space-y-5">
      {/* Response header */}
      <div>
        <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground mb-1">
          Response
        </p>
        {r.description && (
          <p className="text-sm">{r.description}</p>
        )}
      </div>

      {/* Error */}
      {r.error && (
        <Card className="p-3 border-destructive/30 bg-destructive/5">
          <p className="text-sm text-destructive">{r.error}</p>
        </Card>
      )}

      {/* Chart — key forces remount when switching queries so chart state resets */}
      {r.columns.length >= 2 && r.data.length > 0 && (
        <div>
          <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground mb-2">
            Visualization
          </p>
          <Card className="p-4">
            <ChartRenderer
              key={r.message_id || `chart-${msg.question}`}
              suggestion={
                r.chart_suggestion && r.chart_suggestion.chart_type !== "table"
                  ? r.chart_suggestion
                  : { chart_type: "bar", x_axis: r.columns[0], y_axis: r.columns[1], title: "" }
              }
              data={r.data}
              columns={r.columns}
            />
          </Card>
        </div>
      )}

      {/* Table */}
      {r.columns.length > 0 && r.data.length > 0 && (
        <div>
          <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground mb-2">
            Results
            {r.row_count > 0 && (
              <span className="ml-2 text-muted-foreground/60 normal-case tracking-normal">
                {r.row_count} row{r.row_count !== 1 ? "s" : ""}
              </span>
            )}
          </p>
          <Card className="overflow-hidden">
            <DataTable columns={r.columns} data={r.data} className="max-h-80" />
          </Card>
        </div>
      )}

      {/* SQL */}
      {r.sql && (
        <Card className="overflow-hidden">
          <button
            className="w-full flex items-center gap-2 px-4 py-2.5 text-xs text-muted-foreground hover:bg-muted/50 transition-colors"
            onClick={() => setSqlExpanded(!sqlExpanded)}
          >
            {sqlExpanded ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
            <Code2 className="h-3 w-3" />
            SQL Query
          </button>
          {sqlExpanded && (
            <SyntaxHighlighter
              language="sql"
              style={oneDark}
              customStyle={{ margin: 0, borderRadius: 0, fontSize: "0.75rem", padding: "0.75rem" }}
              wrapLongLines
            >
              {r.sql}
            </SyntaxHighlighter>
          )}
        </Card>
      )}
    </div>
  );
}
