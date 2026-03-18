import { AuthProvider } from "@/components/apx/AuthProvider";
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
      <AuthProvider>
        <TooltipProvider>
          <Outlet />
          <Toaster richColors />
        </TooltipProvider>
      </AuthProvider>
    </ThemeProvider>
  ),
});
