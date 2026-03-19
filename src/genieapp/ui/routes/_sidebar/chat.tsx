/**
 * Chat interface — renders the Query Workspace view for the current space.
 */

import { createFileRoute, useSearch } from "@tanstack/react-router";
import { useAppConfig, useSpaceConfig } from "@/lib/api";
import { QueryWorkspace } from "@/components/apx/templates/QueryWorkspace";
import { Loader2 } from "lucide-react";

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
  const { conversationId: initialConvId, spaceId: urlSpaceId } = useSearch({ from: "/_sidebar/chat" });

  const { data: defaultConfig } = useAppConfig();
  const { data: spaceConfig } = useSpaceConfig(urlSpaceId);
  const config = urlSpaceId ? spaceConfig : defaultConfig;

  // Always resolve a spaceId — from URL or from loaded config
  const spaceId = urlSpaceId || config?.space_id;

  if (!config) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <QueryWorkspace
      spaceId={spaceId}
      config={config}
      initialConversationId={initialConvId}
    />
  );
}
