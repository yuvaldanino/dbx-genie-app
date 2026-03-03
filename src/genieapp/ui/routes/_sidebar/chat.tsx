/**
 * Chat interface — send questions to Genie with async status polling.
 */

import { useRef, useEffect, useState, useCallback } from "react";
import { createFileRoute, useSearch } from "@tanstack/react-router";
import {
  useAppConfig,
  useStartChat,
  getChatStatus,
  getChatResult,
  type ChatMessageOut,
} from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { MessageBubble } from "@/components/apx/MessageBubble";
import { WelcomeScreen } from "@/components/apx/WelcomeScreen";
import { Send, Loader2 } from "lucide-react";

interface ChatSearch {
  conversationId?: string;
}

export const Route = createFileRoute("/_sidebar/chat")({
  component: ChatPage,
  validateSearch: (search: Record<string, unknown>): ChatSearch => ({
    conversationId: typeof search.conversationId === "string" ? search.conversationId : undefined,
  }),
});

interface Message {
  question: string;
  response?: ChatMessageOut;
  /** Status text shown during async polling. */
  statusText?: string;
}

const STATUS_LABELS: Record<string, string> = {
  SUBMITTED: "Submitting...",
  FETCHING_METADATA: "Fetching metadata...",
  FILTERING_CONTEXT: "Analyzing context...",
  ASKING_AI: "Generating SQL...",
  PENDING_WAREHOUSE: "Waiting for warehouse...",
  EXECUTING_QUERY: "Running query...",
  COMPLETED: "Complete",
  FAILED: "Failed",
};

function ChatPage() {
  const { data: config } = useAppConfig();
  const { conversationId: initialConvId } = useSearch({ from: "/_sidebar/chat" });
  const startChat = useStartChat();
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [conversationId, setConversationId] = useState<string | undefined>(initialConvId);
  const [isSending, setIsSending] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isSending]);

  const pollAndFetchResult = useCallback(
    async (convId: string, msgId: string, msgIndex: number) => {
      // Poll status until complete
      let attempts = 0;
      const maxAttempts = 300; // 5 minutes at 1s intervals

      while (attempts < maxAttempts) {
        try {
          const status = await getChatStatus(convId, msgId);

          // Update status text
          const label = STATUS_LABELS[status.status] || status.status;
          setMessages((prev) => {
            const updated = [...prev];
            if (updated[msgIndex]) {
              updated[msgIndex] = { ...updated[msgIndex], statusText: label };
            }
            return updated;
          });

          if (status.is_complete) {
            // Fetch the full result
            const result = await getChatResult(convId, msgId);
            setConversationId(result.conversation_id || undefined);
            setMessages((prev) => {
              const updated = [...prev];
              if (updated[msgIndex]) {
                updated[msgIndex] = {
                  question: updated[msgIndex].question,
                  response: result,
                  statusText: undefined,
                };
              }
              return updated;
            });
            return;
          }
        } catch {
          // On error, keep polling
        }

        attempts++;
        await new Promise((r) => setTimeout(r, 1000));
      }

      // Timeout
      setMessages((prev) => {
        const updated = [...prev];
        if (updated[msgIndex]) {
          updated[msgIndex] = {
            question: updated[msgIndex].question,
            response: {
              conversation_id: convId,
              message_id: msgId,
              status: "FAILED",
              description: "",
              sql: "",
              columns: [],
              data: [],
              row_count: 0,
              chart_suggestion: null,
              error: "Request timed out",
              suggested_questions: [],
              query_description: "",
              is_truncated: false,
              is_clarification: false,
              error_type: "TIMEOUT",
            },
          };
        }
        return updated;
      });
    },
    [],
  );

  const handleSend = useCallback(
    (question?: string) => {
      const q = question || input.trim();
      if (!q || isSending) return;
      setInput("");
      setIsSending(true);

      // Add pending message
      const msgIndex = messages.length;
      setMessages((prev) => [...prev, { question: q, statusText: "Submitting..." }]);

      startChat.mutate(
        { question: q, conversationId },
        {
          onSuccess: async (startResult) => {
            const convId = startResult.conversation_id;
            const msgId = startResult.message_id;
            setConversationId(convId || undefined);

            // Start polling
            await pollAndFetchResult(convId, msgId, msgIndex);
            setIsSending(false);
          },
          onError: (error) => {
            setMessages((prev) => {
              const updated = [...prev];
              updated[msgIndex] = {
                question: q,
                response: {
                  conversation_id: conversationId || "",
                  message_id: "",
                  status: "FAILED",
                  description: "",
                  sql: "",
                  columns: [],
                  data: [],
                  row_count: 0,
                  chart_suggestion: null,
                  error: error instanceof Error ? error.message : "Request failed",
                  suggested_questions: [],
                  query_description: "",
                  is_truncated: false,
                  is_clarification: false,
                  error_type: "UNKNOWN",
                },
              };
              return updated;
            });
            setIsSending(false);
          },
        },
      );
    },
    [input, isSending, messages.length, conversationId, startChat, pollAndFetchResult],
  );

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  const hasMessages = messages.length > 0;

  return (
    <div className="flex flex-col h-full">
      {/* Message area */}
      <ScrollArea className="flex-1 p-4" ref={scrollRef}>
        {!hasMessages && config ? (
          <WelcomeScreen
            displayName={config.display_name}
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
                  /* Pending message with status */
                  <div className="space-y-3">
                    <div className="flex justify-end">
                      <div className="bg-primary text-primary-foreground rounded-2xl rounded-tr-sm px-4 py-2.5">
                        <p className="text-sm">{msg.question}</p>
                      </div>
                    </div>
                    <div className="flex justify-start">
                      <div className="flex items-center gap-2 px-4 py-3">
                        <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                        <span className="text-sm text-muted-foreground">
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
      </ScrollArea>

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
