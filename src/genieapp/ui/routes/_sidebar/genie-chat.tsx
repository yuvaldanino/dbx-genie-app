/**
 * Genie Chat route — continuous, ephemeral conversation with the current space.
 * Mirrors chat.tsx's spaceId/config resolution; "New chat" remounts the thread
 * via a key bump to reset useChatFlow state (fresh conversation_id).
 */

import { useState } from "react";
import { createFileRoute, useSearch } from "@tanstack/react-router";
import { useAppConfig, useSpaceConfig } from "@/lib/api";
import { GenieChatThread } from "@/components/apx/genie-chat/GenieChatThread";
import { Loader2 } from "lucide-react";

interface GenieChatSearch {
  spaceId?: string;
}

export const Route = createFileRoute("/_sidebar/genie-chat")({
  component: GenieChatPage,
  validateSearch: (search: Record<string, unknown>): GenieChatSearch => ({
    spaceId: typeof search.spaceId === "string" ? search.spaceId : undefined,
  }),
});

function GenieChatPage() {
  const { spaceId: urlSpaceId } = useSearch({ from: "/_sidebar/genie-chat" });

  const { data: defaultConfig } = useAppConfig();
  const { data: spaceConfig } = useSpaceConfig(urlSpaceId);
  const config = urlSpaceId ? spaceConfig : defaultConfig;
  const spaceId = urlSpaceId || config?.space_id;

  // Bumping the key remounts the thread → fresh useChatFlow → new conversation.
  const [chatKey, setChatKey] = useState(0);

  if (!config) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <GenieChatThread
      key={chatKey}
      spaceId={spaceId}
      config={config}
      onNewChat={() => setChatKey((k) => k + 1)}
    />
  );
}
