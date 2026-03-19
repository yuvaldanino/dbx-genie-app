/**
 * Templates route — redirects to chat (template selection removed).
 */

import { createFileRoute, redirect } from "@tanstack/react-router";

export const Route = createFileRoute("/_sidebar/templates")({
  beforeLoad: () => {
    throw redirect({ to: "/chat" });
  },
});
