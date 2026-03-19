/**
 * Reusable chat flow hook — handles send, poll, and result fetching.
 * Extracted from chat.tsx for use across all template components.
 */

import { useState, useCallback, useRef, useEffect } from "react";
import {
  useStartChat,
  getChatStatus,
  getChatResult,
  useConversationMessages,
  type ChatMessageOut,
} from "./api";

export interface Message {
  question: string;
  response?: ChatMessageOut;
  statusText?: string;
  is_starred?: boolean;
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

interface UseChatFlowOptions {
  spaceId?: string;
  initialConversationId?: string;
}

/**
 * Update the URL search params without triggering a full navigation.
 * Uses replaceState so the browser back button isn't polluted.
 */
function syncSearchParam(key: string, value: string): void {
  const url = new URL(window.location.href);
  url.searchParams.set(key, value);
  window.history.replaceState(null, "", url.toString());
}

export function useChatFlow(options: UseChatFlowOptions = {}) {
  const { spaceId, initialConversationId } = options;
  const startChat = useStartChat();
  const [messages, setMessages] = useState<Message[]>([]);
  const [conversationId, setConversationId] = useState<string | undefined>(
    initialConversationId,
  );
  const [isSending, setIsSending] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Keep conversationId in sync when initialConversationId changes
  // (e.g., auto-loaded from most recent conversation)
  useEffect(() => {
    if (initialConversationId && initialConversationId !== conversationId) {
      setConversationId(initialConversationId);
    }
  }, [initialConversationId]); // eslint-disable-line react-hooks/exhaustive-deps

  // Load conversation messages when navigating from history
  const { data: loadedMessages } = useConversationMessages(conversationId, spaceId);
  const [loadedConvId, setLoadedConvId] = useState<string | undefined>();

  useEffect(() => {
    if (loadedMessages && conversationId && conversationId !== loadedConvId) {
      setLoadedConvId(conversationId);
      setMessages(
        loadedMessages.map((m) => ({
          question: m.question,
          response: m.response ?? undefined,
          is_starred: m.is_starred ?? false,
        })),
      );
    }
  }, [loadedMessages, conversationId, loadedConvId]);

  // Auto-scroll
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isSending]);

  const pollAndFetchResult = useCallback(
    async (convId: string, msgId: string, msgIndex: number) => {
      let attempts = 0;
      const maxAttempts = 300;

      while (attempts < maxAttempts) {
        try {
          const status = await getChatStatus(convId, msgId, spaceId);
          const label = STATUS_LABELS[status.status] || status.status;
          setMessages((prev) => {
            const updated = [...prev];
            if (updated[msgIndex]) {
              updated[msgIndex] = { ...updated[msgIndex], statusText: label };
            }
            return updated;
          });

          if (status.is_complete) {
            const result = await getChatResult(convId, msgId, spaceId);
            setConversationId(result.conversation_id || undefined);
            // Sync conversationId + spaceId to URL so refresh works
            if (result.conversation_id) {
              syncSearchParam("conversationId", result.conversation_id);
            }
            if (spaceId) {
              syncSearchParam("spaceId", spaceId);
            }
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
    [spaceId],
  );

  const sendMessage = useCallback(
    (question: string) => {
      if (!question.trim() || isSending) return;
      setIsSending(true);

      const msgIndex = messages.length;
      setMessages((prev) => [...prev, { question, statusText: "Submitting..." }]);

      startChat.mutate(
        { question, conversationId, spaceId },
        {
          onSuccess: async (startResult) => {
            const convId = startResult.conversation_id;
            const msgId = startResult.message_id;
            setConversationId(convId || undefined);
            // Sync conversationId + spaceId to URL immediately
            if (convId) {
              syncSearchParam("conversationId", convId);
            }
            if (spaceId) {
              syncSearchParam("spaceId", spaceId);
            }
            await pollAndFetchResult(convId, msgId, msgIndex);
            setIsSending(false);
          },
          onError: (error) => {
            setMessages((prev) => {
              const updated = [...prev];
              updated[msgIndex] = {
                question,
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
    [isSending, messages.length, conversationId, spaceId, startChat, pollAndFetchResult],
  );

  return {
    messages,
    setMessages,
    isSending,
    conversationId,
    sendMessage,
    scrollRef,
  };
}
