/**
 * Hex → OKLCH conversion and theme derivation from brand colors.
 * Converts 3 brand colors + 5 chart colors into ~30 CSS variable overrides.
 *
 * Improved dark mode: deeper background, less muddy neutrals, lightness
 * floor on primary/accent/charts, lightness spread for clustered chart colors.
 */

import { parse, converter } from "culori";

const toOklch = converter("oklch");

/** Convert a hex color to an OKLCH CSS string. */
export function hexToOklch(hex: string): string {
  const color = parse(hex);
  if (!color) return hex;
  const oklch = toOklch(color);
  const l = oklch.l?.toFixed(4) ?? "0.5";
  const c = oklch.c?.toFixed(4) ?? "0.1";
  const h = oklch.h?.toFixed(2) ?? "0";
  return `oklch(${l} ${c} ${h})`;
}

/** Adjust lightness of an OKLCH color string. */
function adjustLightness(oklchStr: string, delta: number): string {
  const match = oklchStr.match(
    /oklch\(\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*\)/,
  );
  if (!match) return oklchStr;
  const l = Math.min(1, Math.max(0, parseFloat(match[1]) + delta));
  return `oklch(${l.toFixed(4)} ${match[2]} ${match[3]})`;
}

/** Clamp lightness to a minimum floor. */
function clampLightness(oklchStr: string, minL: number): string {
  const l = extractLightness(oklchStr);
  if (l >= minL) return oklchStr;
  const match = oklchStr.match(
    /oklch\(\s*[\d.]+\s+([\d.]+)\s+([\d.]+)\s*\)/,
  );
  if (!match) return oklchStr;
  return `oklch(${minL.toFixed(4)} ${match[1]} ${match[2]})`;
}

/** Create a tinted neutral from a hue — low chroma, adjustable lightness. */
function tintedNeutral(hue: number, lightness: number, chroma = 0.01): string {
  return `oklch(${lightness.toFixed(4)} ${chroma.toFixed(4)} ${hue.toFixed(2)})`;
}

/** Extract the hue from an OKLCH string. */
function extractHue(oklchStr: string): number {
  const match = oklchStr.match(
    /oklch\(\s*[\d.]+\s+[\d.]+\s+([\d.]+)\s*\)/,
  );
  return match ? parseFloat(match[1]) : 255;
}

/** Extract the lightness (L) from an OKLCH string. */
function extractLightness(oklchStr: string): number {
  const match = oklchStr.match(
    /oklch\(\s*([\d.]+)\s+[\d.]+\s+[\d.]+\s*\)/,
  );
  return match ? parseFloat(match[1]) : 0.5;
}

/** Extract the chroma (C) from an OKLCH string. */
function extractChroma(oklchStr: string): number {
  const match = oklchStr.match(
    /oklch\(\s*[\d.]+\s+([\d.]+)\s+[\d.]+\s*\)/,
  );
  return match ? parseFloat(match[1]) : 0.1;
}

/**
 * Spread chart colors by lightness if they're too clustered.
 * Keeps brand hues intact — only redistributes lightness values.
 */
function spreadChartLightness(charts: string[]): string[] {
  const lights = charts.map(extractLightness);
  const range = Math.max(...lights) - Math.min(...lights);

  if (range >= 0.15) return charts; // Already spread enough

  // Redistribute to target lightness levels while keeping hue + chroma
  const targets = [0.65, 0.55, 0.75, 0.60, 0.70];
  return charts.map((c, i) => {
    const ch = Math.max(extractChroma(c), 0.08);
    const h = extractHue(c);
    return `oklch(${(targets[i] ?? 0.60).toFixed(4)} ${ch.toFixed(4)} ${h.toFixed(2)})`;
  });
}

interface ThemeInput {
  primary: string;
  secondary: string;
  accent: string;
  chartColors: string[];
}

/**
 * Derive a full set of CSS variable overrides from brand colors.
 * Returns a Record mapping CSS variable names to OKLCH values.
 */
export function deriveTheme(
  input: ThemeInput,
  mode: "light" | "dark",
): Record<string, string> {
  const primary = hexToOklch(input.primary);
  const accent = hexToOklch(input.accent);
  const charts = input.chartColors.map(hexToOklch);
  const hue = extractHue(primary);

  const darkBump = mode === "dark" ? 0.10 : 0;

  const vars: Record<string, string> = {};

  // Branded colors — bump + enforce minimum lightness in dark mode
  vars["--primary"] = darkBump
    ? clampLightness(adjustLightness(primary, darkBump), 0.55)
    : primary;
  vars["--accent"] = darkBump
    ? clampLightness(adjustLightness(accent, darkBump), 0.55)
    : accent;
  vars["--ring"] = vars["--primary"];
  vars["--sidebar-primary"] = vars["--primary"];
  vars["--sidebar-ring"] = vars["--primary"];

  // Foregrounds — auto-flip to dark text when background is light
  const primaryL = extractLightness(vars["--primary"]);
  const accentL = extractLightness(vars["--accent"]);
  vars["--primary-foreground"] =
    primaryL > 0.62 ? `oklch(0.15 0.02 ${hue.toFixed(2)})` : "oklch(0.99 0 0)";
  vars["--accent-foreground"] =
    accentL > 0.62 ? `oklch(0.15 0.02 ${hue.toFixed(2)})` : "oklch(0.99 0 0)";
  vars["--sidebar-primary-foreground"] =
    primaryL > 0.62 ? `oklch(0.15 0.02 ${hue.toFixed(2)})` : "oklch(0.99 0 0)";

  // Derived tinted neutrals from primary hue
  if (mode === "light") {
    vars["--background"] = tintedNeutral(hue, 0.99, 0.003);
    vars["--foreground"] = tintedNeutral(hue, 0.15, 0.02);
    vars["--card"] = tintedNeutral(hue, 0.99, 0.003);
    vars["--card-foreground"] = tintedNeutral(hue, 0.15, 0.02);
    vars["--popover"] = tintedNeutral(hue, 0.99, 0.003);
    vars["--popover-foreground"] = tintedNeutral(hue, 0.15, 0.02);
    vars["--muted"] = tintedNeutral(hue, 0.95, 0.01);
    vars["--muted-foreground"] = tintedNeutral(hue, 0.45, 0.02);
    vars["--secondary"] = tintedNeutral(hue, 0.95, 0.01);
    vars["--secondary-foreground"] = tintedNeutral(hue, 0.25, 0.05);
    vars["--border"] = tintedNeutral(hue, 0.91, 0.005);
    vars["--input"] = tintedNeutral(hue, 0.91, 0.005);
    vars["--sidebar"] = tintedNeutral(hue, 0.97, 0.005);
    vars["--sidebar-accent"] = tintedNeutral(hue, 0.93, 0.02);
    vars["--sidebar-accent-foreground"] = tintedNeutral(hue, 0.25, 0.05);
    vars["--sidebar-border"] = tintedNeutral(hue, 0.90, 0.01);
  } else {
    // Dark mode — improved contrast, less muddy neutrals
    vars["--background"] = tintedNeutral(hue, 0.13, 0.015);
    vars["--foreground"] = tintedNeutral(hue, 0.93, 0.01);
    vars["--card"] = tintedNeutral(hue, 0.21, 0.015);
    vars["--card-foreground"] = tintedNeutral(hue, 0.93, 0.01);
    vars["--popover"] = tintedNeutral(hue, 0.21, 0.015);
    vars["--popover-foreground"] = tintedNeutral(hue, 0.93, 0.01);
    vars["--muted"] = tintedNeutral(hue, 0.27, 0.015);
    vars["--muted-foreground"] = tintedNeutral(hue, 0.65, 0.02);
    vars["--secondary"] = tintedNeutral(hue, 0.27, 0.015);
    vars["--secondary-foreground"] = "oklch(0.90 0 0)";
    vars["--border"] = tintedNeutral(hue, 0.33, 0.015);
    vars["--input"] = tintedNeutral(hue, 0.33, 0.015);
    vars["--sidebar"] = tintedNeutral(hue, 0.15, 0.015);
    vars["--sidebar-accent"] = tintedNeutral(hue, 0.22, 0.015);
    vars["--sidebar-accent-foreground"] = "oklch(0.90 0 0)";
    vars["--sidebar-border"] = tintedNeutral(hue, 0.30, 0.015);
  }

  // Chart colors — bump, clamp floor, spread lightness if clustered
  let processedCharts = charts.map((c) =>
    darkBump ? clampLightness(adjustLightness(c, darkBump), 0.45) : c,
  );
  if (mode === "dark") {
    processedCharts = spreadChartLightness(processedCharts);
  }
  for (let i = 0; i < 5; i++) {
    vars[`--chart-${i + 1}`] = processedCharts[i] ?? processedCharts[0];
  }

  return vars;
}
