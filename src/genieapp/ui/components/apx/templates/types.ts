/**
 * Shared props interface for all real template components.
 */

import type { AppConfigOut } from "@/lib/api";

export interface TemplateProps {
  spaceId?: string;
  config: AppConfigOut;
  initialConversationId?: string;
  /** Question to auto-send once on mount (from the ?ask= URL param). */
  initialQuestion?: string;
}
