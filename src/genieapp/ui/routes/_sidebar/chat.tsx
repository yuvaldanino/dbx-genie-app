/**
 * Chat interface — send questions to Genie with async status polling.
 * Supports multi-space via spaceId search param.
 * Uses useChatFlow hook for reusable polling logic.
 */

import { useState } from "react";
import { createFileRoute, useSearch } from "@tanstack/react-router";
import {
  useAppConfig,
  useSpaceConfig,
} from "@/lib/api";
import { useChatFlow } from "@/lib/useChatFlow";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { MessageBubble } from "@/components/apx/MessageBubble";
import { WelcomeScreen } from "@/components/apx/WelcomeScreen";
import { Send, Loader2 } from "lucide-react";

interface ChatSearch {
  conversationId?: string;
  spaceId?: string;
}

export const Route = createFileRoute("/_sidebar/chat")({
  component: ChatPage,
  validateSearch: (search: Record<string, unknown>): ChatSearch => ({
    conversationId: typeof search.conversationId === "string" ? search.conversationId : undefined,
    spaceId: typeof search.spaceId === "string" ? search.spaceId : undefined,
  }),
});

function ChatPage() {
  const { conversationId: initialConvId, spaceId } = useSearch({ from: "/_sidebar/chat" });

  const { data: defaultConfig } = useAppConfig();
  const { data: spaceConfig } = useSpaceConfig(spaceId);
  const config = spaceId ? spaceConfig : defaultConfig;

  const { messages, isSending, sendMessage, scrollRef } = useChatFlow({
    spaceId,
    initialConversationId: initialConvId,
  });

  const [input, setInput] = useState("");

  function handleSend(question?: string) {
    const q = question || input.trim();
    if (!q) return;
    setInput("");
    sendMessage(q);
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  const hasMessages = messages.length > 0;

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Message area */}
      <div className="flex-1 min-h-0 overflow-y-auto p-4" ref={scrollRef}>
        {!hasMessages && config ? (
          <WelcomeScreen
            displayName={config.display_name}
            companyName={config.branding?.company_name}
            logoPath={config.branding?.logo_path}
            sampleQuestions={config.sample_questions}
            onSelectQuestion={handleSend}
          />
        ) : (
          <div className="space-y-6 max-w-4xl mx-auto pb-4">
            {messages.map((msg, i) => (
              <div key={i}>
                {msg.response ? (
                  <MessageBubble
                    question={msg.question}
                    response={msg.response}
                    onAskQuestion={handleSend}
                  />
                ) : (
                  <div className="space-y-3">
                    <div className="flex justify-end">
                      <div className="bg-primary text-primary-foreground rounded-2xl rounded-tr-sm px-4 py-2.5">
                        <p className="text-sm">{msg.question}</p>
                      </div>
                    </div>
                    <div className="flex justify-start">
                      <div className="flex items-center gap-2 px-4 py-3">
                        <Loader2 className="h-4 w-4 animate-spin text-accent" />
                        <span className="text-sm text-accent">
                          {msg.statusText || "Thinking..."}
                        </span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Input bar */}
      <div className="border-t bg-background p-4">
        <div className="max-w-4xl mx-auto flex gap-2">
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
