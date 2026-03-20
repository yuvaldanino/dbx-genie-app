/**
 * Slide-out Genie chat drawer — overlays the dashboard for quick Q&A.
 */

import { useState, useRef, useEffect } from "react";
import { X, Send, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ChartRenderer } from "./ChartRenderer";
import { DataTable } from "./DataTable";
import { useChatFlow } from "@/lib/useChatFlow";
import type { AppConfigOut } from "@/lib/api";

interface GenieDrawerProps {
  open: boolean;
  onClose: () => void;
  spaceId?: string;
  config: AppConfigOut;
}

export function GenieDrawer({ open, onClose, spaceId, config }: GenieDrawerProps) {
  const { messages, isSending, sendMessage, scrollRef } = useChatFlow({ spaceId, ephemeral: true });
  const [input, setInput] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 300);
    }
  }, [open]);

  const handleSend = () => {
    if (!input.trim()) return;
    sendMessage(input.trim());
    setInput("");
  };

  return (
    <>
      {/* Backdrop */}
      {open && (
        <div
          className="fixed inset-0 bg-black/30 z-40"
          onClick={onClose}
        />
      )}

      {/* Drawer panel */}
      <div
        className={`fixed top-0 right-0 h-full w-[420px] max-w-[90vw] bg-background border-l shadow-xl z-50 flex flex-col transition-transform duration-300 ${
          open ? "translate-x-0" : "translate-x-full"
        }`}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b px-4 py-3 shrink-0">
          <div>
            <h2 className="font-semibold text-sm">Ask Genie</h2>
            <p className="text-xs text-muted-foreground">{config.branding.company_name}</p>
          </div>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>

        {/* Messages */}
        <ScrollArea className="flex-1" ref={scrollRef}>
          <div className="p-4 space-y-4">
            {messages.length === 0 && (
              <p className="text-sm text-muted-foreground text-center py-8">
                Ask a question about your data
              </p>
            )}
            {messages.map((msg, i) => (
              <div key={i} className="space-y-2">
                {/* User question */}
                <div className="flex justify-end">
                  <div className="bg-primary text-primary-foreground rounded-2xl rounded-tr-sm px-3 py-2 max-w-[85%]">
                    <p className="text-sm">{msg.question}</p>
                  </div>
                </div>

                {/* Status or response */}
                {msg.statusText && !msg.response && (
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <Loader2 className="h-3 w-3 animate-spin" />
                    {msg.statusText}
                  </div>
                )}

                {msg.response && (
                  <Card className="overflow-hidden border-accent/30 bg-accent/5">
                    <div className="p-3 space-y-2">
                      {msg.response.error && (
                        <p className="text-xs text-destructive">{msg.response.error}</p>
                      )}
                      {msg.response.description && (
                        <p className="text-sm">{msg.response.description}</p>
                      )}
                      {msg.response.columns.length >= 2 &&
                        msg.response.data.length > 0 &&
                        msg.response.chart_suggestion &&
                        msg.response.chart_suggestion.chart_type !== "table" && (
                          <ChartRenderer
                            suggestion={msg.response.chart_suggestion}
                            data={msg.response.data}
                            columns={msg.response.columns}
                          />
                        )}
                      {msg.response.columns.length > 0 && msg.response.data.length > 0 && (
                        <DataTable
                          columns={msg.response.columns}
                          data={msg.response.data}
                          className="max-h-48 border rounded-md"
                        />
                      )}
                    </div>
                  </Card>
                )}
              </div>
            ))}
          </div>
        </ScrollArea>

        {/* Input bar */}
        <div className="border-t p-3 shrink-0">
          <div className="flex gap-2">
            <input
              ref={inputRef}
              type="text"
              className="flex-1 h-9 px-3 rounded-md border bg-background text-sm focus:outline-none focus:ring-1 focus:ring-primary"
              placeholder="Ask a question..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSend()}
              disabled={isSending}
            />
            <Button
              size="icon"
              className="h-9 w-9 shrink-0"
              onClick={handleSend}
              disabled={isSending || !input.trim()}
            >
              {isSending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </Button>
          </div>
        </div>
      </div>
    </>
  );
}
