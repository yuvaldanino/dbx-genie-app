/**
 * Shared props interface for all real template components.
 */

import type { AppConfigOut } from "@/lib/api";

export interface TemplateProps {
  spaceId?: string;
  config: AppConfigOut;
  initialConversationId?: string;
}
