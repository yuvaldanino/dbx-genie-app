/**
 * Genie Chat thread — continuous, ChatGPT-style conversation with a space.
 * Ephemeral by design: nothing is persisted; each mount is a fresh thread.
 * Composes the existing MessageBubble for completed turns; renders its own
 * pending bubble (user question + typing indicator) while Genie works.
 */

import { useRef, useState } from "react";
import { useChatFlow } from "@/lib/useChatFlow";
import type { AppConfigOut } from "@/lib/api";
import { MessageBubble } from "@/components/apx/MessageBubble";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Loader2, Plus, Send, Sparkles, User } from "lucide-react";

interface GenieChatThreadProps {
  spaceId?: string;
  config: AppConfigOut;
  onNewChat: () => void;
}

/** User question bubble for in-flight messages (matches MessageBubble's style). */
function PendingTurn({ question, statusText }: { question: string; statusText?: string }) {
  return (
    <div className="space-y-3">
      <div className="flex justify-end">
        <div className="flex items-start gap-2 max-w-[80%]">
          <div className="bg-primary text-primary-foreground rounded-2xl rounded-tr-sm px-4 py-2.5">
            <p className="text-sm">{question}</p>
          </div>
          <div className="shrink-0 w-8 h-8 rounded-full bg-primary/15 flex items-center justify-center">
            <User className="h-4 w-4 text-primary" />
          </div>
        </div>
      </div>
      <div className="flex justify-start">
        <Card className="border-accent/30 bg-accent/5">
          <div className="px-4 py-3 flex items-center gap-2.5">
            <span className="flex gap-1">
              <span className="h-1.5 w-1.5 rounded-full bg-primary/60 animate-bounce [animation-delay:0ms]" />
              <span className="h-1.5 w-1.5 rounded-full bg-primary/60 animate-bounce [animation-delay:150ms]" />
              <span className="h-1.5 w-1.5 rounded-full bg-primary/60 animate-bounce [animation-delay:300ms]" />
            </span>
            <span className="text-xs text-muted-foreground">
              {statusText || "Thinking…"}
            </span>
          </div>
        </Card>
      </div>
    </div>
  );
}

export function GenieChatThread({ spaceId, config, onNewChat }: GenieChatThreadProps) {
  // No initialConversationId + ephemeral → fresh, unpersisted thread per mount.
  const { messages, isSending, sendMessage, scrollRef } = useChatFlow({
    spaceId,
    ephemeral: true,
  });
  const [input, setInput] = useState("");
  const inputRef = useRef<HTMLTextAreaElement>(null);

  function handleSend(question?: string) {
    const q = (question ?? input).trim();
    if (!q || isSending) return;
    setInput("");
    sendMessage(q);
    inputRef.current?.focus();
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  const empty = messages.length === 0;

  return (
    <div className="flex flex-col h-full min-h-0 overflow-hidden">
      {/* Header */}
      <div className="border-b px-4 py-2.5 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2 min-w-0">
          <Sparkles className="h-4 w-4 text-primary shrink-0" />
          <span className="text-sm font-medium truncate">
            Genie Chat — {config.display_name}
          </span>
          <span className="text-[10px] text-muted-foreground hidden sm:inline">
            free-form · not saved
          </span>
        </div>
        <Button
          variant="outline"
          size="sm"
          className="gap-1.5 text-xs shrink-0"
          onClick={onNewChat}
          disabled={isSending}
        >
          <Plus className="h-3.5 w-3.5" />
          New chat
        </Button>
      </div>

      {/* Thread (plain overflow div so useChatFlow's scrollRef auto-scroll works).
          min-h-0: Safari needs the explicit flex minimum to keep this scroller
          contained. overscroll-contain: when the thread hits its end, do NOT
          chain the scroll to the document (whole-page bounce below the input). */}
      <div ref={scrollRef} className="flex-1 min-h-0 overflow-y-auto overscroll-contain">
        <div className="max-w-3xl mx-auto px-4 py-6 space-y-6">
          {empty ? (
            <div className="flex flex-col items-center justify-center text-center pt-16 gap-4">
              {config.branding?.logo_path ? (
                <img
                  src={config.branding.logo_path}
                  alt={config.branding.company_name}
                  className="h-12 w-auto opacity-90"
                />
              ) : (
                <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center">
                  <Sparkles className="h-6 w-6 text-primary" />
                </div>
              )}
              <div>
                <h2 className="text-lg font-semibold">
                  Chat with {config.branding?.company_name || config.display_name}
                </h2>
                <p className="text-sm text-muted-foreground mt-1">
                  A continuous conversation with your data — follow-ups build on
                  previous answers. This thread isn't saved.
                </p>
              </div>
              {config.sample_questions.length > 0 && (
                <div className="flex flex-wrap justify-center gap-2 max-w-xl pt-2">
                  {config.sample_questions.slice(0, 5).map((q) => (
                    <Button
                      key={q}
                      variant="outline"
                      size="sm"
                      className="h-auto py-1.5 px-3 text-xs font-normal"
                      onClick={() => handleSend(q)}
                    >
                      {q}
                    </Button>
                  ))}
                </div>
              )}
            </div>
          ) : (
            messages.map((msg, i) =>
              msg.response ? (
                <MessageBubble
                  key={msg.response.message_id || i}
                  question={msg.question}
                  response={msg.response}
                  onAskQuestion={(q) => handleSend(q)}
                  spaceId={spaceId}
                  hideExport
                />
              ) : (
                <PendingTurn key={`pending-${i}`} question={msg.question} statusText={msg.statusText} />
              ),
            )
          )}
        </div>
      </div>

      {/* Input bar */}
      <div className="border-t p-4 shrink-0">
        <div className="max-w-3xl mx-auto flex items-end gap-2">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={`Ask ${config.branding?.company_name || "Genie"} anything… (Enter to send, Shift+Enter for newline)`}
            rows={Math.min(4, Math.max(1, input.split("\n").length))}
            disabled={isSending}
            className="flex-1 resize-none rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-xs outline-none transition-[color,box-shadow] placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px] disabled:cursor-not-allowed disabled:opacity-50"
          />
          <Button
            onClick={() => handleSend()}
            disabled={isSending || !input.trim()}
            size="icon"
            className="shrink-0"
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
  );
}
