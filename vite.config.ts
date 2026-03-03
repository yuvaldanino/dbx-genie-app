import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { TanStackRouterVite } from "@tanstack/router-plugin/vite";
import { resolve } from "path";

const uiRoot = resolve(__dirname, "src/genieapp/ui");

export default defineConfig({
  root: uiRoot,
  publicDir: resolve(uiRoot, "public"),
  plugins: [
    TanStackRouterVite({
      routesDirectory: resolve(uiRoot, "routes"),
      generatedRouteTree: resolve(uiRoot, "types/routeTree.gen.ts"),
      quoteStyle: "double",
    }),
    react(),
    tailwindcss(),
  ],
  resolve: {
    alias: {
      "@": uiRoot,
    },
  },
  define: {
    __APP_NAME__: JSON.stringify("genieapp"),
  },
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: resolve(__dirname, "src/genieapp/__dist__"),
    emptyOutDir: true,
  },
});
