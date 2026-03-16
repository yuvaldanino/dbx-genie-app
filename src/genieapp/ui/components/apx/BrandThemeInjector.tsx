/**
 * Injects brand CSS variable overrides onto :root at runtime.
 * Reads branding from config, converts hex → OKLCH, and sets ~30 CSS vars.
 * Cleans up on unmount to restore defaults.
 */

import { useEffect, useRef } from "react";
import { useTheme } from "@/components/apx/theme-provider";
import { deriveTheme } from "@/lib/color-utils";
import type { BrandingOut } from "@/lib/api";

interface BrandThemeInjectorProps {
  branding: BrandingOut | null | undefined;
}

export function BrandThemeInjector({ branding }: BrandThemeInjectorProps) {
  const { theme } = useTheme();
  const appliedVarsRef = useRef<string[]>([]);

  const resolvedMode =
    theme === "dark" ||
    (theme === "system" &&
      window.matchMedia("(prefers-color-scheme: dark)").matches)
      ? "dark"
      : "light";

  useEffect(() => {
    // Clean up previous overrides
    const cleanup = () => {
      for (const varName of appliedVarsRef.current) {
        document.documentElement.style.removeProperty(varName);
      }
      appliedVarsRef.current = [];
    };

    if (!branding?.primary_color) {
      cleanup();
      return;
    }

    const vars = deriveTheme(
      {
        primary: branding.primary_color,
        secondary: branding.secondary_color,
        accent: branding.accent_color || branding.primary_color,
        chartColors: branding.chart_colors?.length
          ? branding.chart_colors
          : [branding.primary_color, branding.secondary_color, branding.accent_color || branding.primary_color],
      },
      resolvedMode,
    );

    cleanup();
    for (const [varName, value] of Object.entries(vars)) {
      document.documentElement.style.setProperty(varName, value);
    }
    appliedVarsRef.current = Object.keys(vars);

    // Set favicon to logo if available
    if (branding.logo_path) {
      let link = document.querySelector<HTMLLinkElement>("link[rel~='icon']");
      if (!link) {
        link = document.createElement("link");
        link.rel = "icon";
        document.head.appendChild(link);
      }
      link.href = branding.logo_path;
    }

    return cleanup;
  }, [branding, resolvedMode]);

  return null;
}
