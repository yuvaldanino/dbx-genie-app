import { ThemeProvider } from "@/components/apx/theme-provider";
import { QueryClient } from "@tanstack/react-query";
import { createRootRouteWithContext, Outlet } from "@tanstack/react-router";
import { Toaster } from "sonner";
import { TooltipProvider } from "@/components/ui/tooltip";

export const Route = createRootRouteWithContext<{
  queryClient: QueryClient;
}>()({
  component: () => (
    <ThemeProvider defaultTheme="dark" storageKey="genieapp-theme">
      <TooltipProvider>
        <Outlet />
        <Toaster richColors />
      </TooltipProvider>
    </ThemeProvider>
  ),
});
