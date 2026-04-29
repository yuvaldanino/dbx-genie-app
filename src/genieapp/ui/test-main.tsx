/**
 * Sandbox entry — bootstraps React with theme + styles, NO router or auth.
 * Served at http://localhost:5173/test.html
 *
 * Includes CSS overrides for improved dark-mode contrast (testing only).
 */

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "@/styles/globals.css";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "@/components/apx/theme-provider";
import { SandboxApp } from "./test-sandbox";

/**
 * Dark mode contrast overrides — bump card/border lightness so components
 * visually separate from the background.
 *
 * Original values → New values:
 *   --background: 0.14 (was 0.16, deeper for more contrast range)
 *   --card:       0.22 (was 0.19, noticeably lighter than bg)
 *   --border:     0.33 (was 0.28, visible edge on cards)
 *   --muted:      0.27 (was 0.25, slightly more distinct)
 */
const contrastOverrides = document.createElement("style");
contrastOverrides.textContent = `
  .dark {
    --background: oklch(0.13 0.01 260);
    --card: oklch(0.21 0.015 260);
    --border: oklch(0.33 0.015 260);
    --input: oklch(0.33 0.015 260);
    --muted: oklch(0.27 0.01 260);
    --secondary: oklch(0.27 0.02 260);
  }
`;
document.head.appendChild(contrastOverrides);

const queryClient = new QueryClient();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <ThemeProvider defaultTheme="dark" storageKey="genieapp-theme">
        <SandboxApp />
      </ThemeProvider>
    </QueryClientProvider>
  </StrictMode>,
);
