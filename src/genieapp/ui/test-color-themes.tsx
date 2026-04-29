/**
 * Sandbox for testing brand color theme derivation.
 *
 * Shows: side-by-side CURRENT vs IMPROVED, plus a mock Genie Space preview
 * using the improved theme to show how colors look in real chart/card context.
 *
 * V2: Lightness spread (not hue spread) — keeps brand identity.
 */

import { useState } from "react";
import { parse, converter } from "culori";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend,
} from "recharts";
import { Sparkles, Code2, ChevronRight, MessageSquare } from "lucide-react";
import Markdown from "react-markdown";

const toOklch = converter("oklch");

// ---------------------------------------------------------------------------
// OKLCH helpers
// ---------------------------------------------------------------------------

function hexToOklch(hex: string): string {
  const color = parse(hex);
  if (!color) return hex;
  const oklch = toOklch(color);
  return `oklch(${(oklch.l ?? 0.5).toFixed(4)} ${(oklch.c ?? 0.1).toFixed(4)} ${(oklch.h ?? 0).toFixed(2)})`;
}

function extractL(s: string): number {
  const m = s.match(/oklch\(\s*([\d.]+)/);
  return m ? parseFloat(m[1]) : 0.5;
}
function extractC(s: string): number {
  const m = s.match(/oklch\(\s*[\d.]+\s+([\d.]+)/);
  return m ? parseFloat(m[1]) : 0.1;
}
function extractH(s: string): number {
  const m = s.match(/oklch\(\s*[\d.]+\s+[\d.]+\s+([\d.]+)/);
  return m ? parseFloat(m[1]) : 255;
}
function makeOklch(l: number, c: number, h: number): string {
  return `oklch(${l.toFixed(4)} ${c.toFixed(4)} ${h.toFixed(2)})`;
}
function adjustL(s: string, delta: number): string {
  return makeOklch(Math.min(1, Math.max(0, extractL(s) + delta)), extractC(s), extractH(s));
}
function clampL(s: string, minL: number): string {
  const l = extractL(s);
  return l >= minL ? s : makeOklch(minL, extractC(s), extractH(s));
}
function tinted(hue: number, l: number, c = 0.01): string {
  return makeOklch(l, c, hue);
}

// ---------------------------------------------------------------------------
// CURRENT deriveTheme (from color-utils.ts)
// ---------------------------------------------------------------------------

interface DerivedTheme {
  primary: string;
  accent: string;
  background: string;
  card: string;
  border: string;
  muted: string;
  charts: string[];
}

function deriveThemeCurrent(primary: string, accent: string, chartColors: string[]): DerivedTheme {
  const p = hexToOklch(primary);
  const a = hexToOklch(accent);
  const charts = chartColors.map(hexToOklch);
  const hue = extractH(p);

  return {
    primary: adjustL(p, 0.07),
    accent: adjustL(a, 0.07),
    background: tinted(hue, 0.18, 0.035),
    card: tinted(hue, 0.22, 0.04),
    border: tinted(hue, 0.30, 0.025),
    muted: tinted(hue, 0.26, 0.03),
    charts: charts.map((c) => adjustL(c, 0.07)),
  };
}

// ---------------------------------------------------------------------------
// IMPROVED deriveTheme — lightness spread, keeps brand hues
// ---------------------------------------------------------------------------

/** Spread chart colors by lightness if any two are too close. Keep hues intact. */
function spreadLightness(charts: string[]): string[] {
  const parsed = charts.map((c) => ({ l: extractL(c), ch: extractC(c), h: extractH(c) }));

  // Target lightness levels for 5 chart colors on dark bg
  const targets = [0.65, 0.55, 0.75, 0.60, 0.70];

  // Check if lightness values are too clustered (all within 0.15 range)
  const lights = parsed.map((p) => p.l);
  const range = Math.max(...lights) - Math.min(...lights);

  if (range < 0.15) {
    // Too clustered — redistribute lightness while keeping hue+chroma
    return parsed.map((p, i) => makeOklch(targets[i], Math.max(p.ch, 0.08), p.h));
  }

  // Not clustered — just ensure minimum
  return charts;
}

function deriveThemeImproved(primary: string, accent: string, chartColors: string[]): DerivedTheme {
  const p = hexToOklch(primary);
  const a = hexToOklch(accent);
  const charts = chartColors.map(hexToOklch);
  const hue = extractH(p);

  // Bump + floor primary/accent
  const pFinal = clampL(adjustL(p, 0.10), 0.55);
  const aFinal = clampL(adjustL(a, 0.10), 0.55);

  // Better neutrals — less chroma, more contrast
  const bg     = tinted(hue, 0.13, 0.015);
  const card   = tinted(hue, 0.21, 0.015);
  const border = tinted(hue, 0.33, 0.015);
  const muted  = tinted(hue, 0.27, 0.015);

  // Chart colors: bump, floor, then spread lightness if clustered
  let processed = charts.map((c) => clampL(adjustL(c, 0.10), 0.45));
  processed = spreadLightness(processed);

  return {
    primary: pFinal,
    accent: aFinal,
    background: bg,
    card,
    border,
    muted,
    charts: processed,
  };
}

// ---------------------------------------------------------------------------
// Brand palettes
// ---------------------------------------------------------------------------

interface BrandPalette {
  name: string;
  primary: string;
  accent: string;
  chart_colors: string[];
}

const BRANDS: BrandPalette[] = [
  {
    name: "Nike",
    primary: "#111111",
    accent: "#FA5400",
    chart_colors: ["#FA5400", "#111111", "#767676", "#C4C4C4", "#FF8C00"],
  },
  {
    name: "Forkable",
    primary: "#10B981",
    accent: "#F59E0B",
    chart_colors: ["#10B981", "#3B82F6", "#F59E0B", "#EF4444", "#8B5CF6"],
  },
  {
    name: "Starbucks",
    primary: "#00704A",
    accent: "#D4E9E2",
    chart_colors: ["#00704A", "#1E3932", "#D4E9E2", "#CBA258", "#FFFFFF"],
  },
  {
    name: "Coca-Cola",
    primary: "#F40009",
    accent: "#FFFFFF",
    chart_colors: ["#F40009", "#000000", "#8B0000", "#CC0000", "#FF3333"],
  },
  {
    name: "Spotify",
    primary: "#1DB954",
    accent: "#1ED760",
    chart_colors: ["#1DB954", "#1ED760", "#169C46", "#535353", "#B3B3B3"],
  },
];

// Mock chart data for the Genie Space preview
const MOCK_CHART_DATA = [
  { category: "North America", value: 4200 },
  { category: "Europe", value: 3100 },
  { category: "Asia Pacific", value: 2800 },
  { category: "Latin America", value: 1500 },
  { category: "Middle East", value: 900 },
];

const MOCK_PIE_DATA = [
  { name: "Product A", value: 42 },
  { name: "Product B", value: 28 },
  { name: "Product C", value: 18 },
  { name: "Product D", value: 8 },
  { name: "Product E", value: 4 },
];

// ---------------------------------------------------------------------------
// Small theme preview (side-by-side)
// ---------------------------------------------------------------------------

function ThemePreview({ label, theme }: { label: string; theme: DerivedTheme }) {
  return (
    <div className="flex-1 min-w-0">
      <p className="text-xs font-medium mb-2 text-center">{label}</p>
      <div
        className="rounded-lg overflow-hidden border"
        style={{ backgroundColor: theme.background, borderColor: theme.border }}
      >
        <div className="h-1.5" style={{ backgroundColor: theme.primary }} />
        <div className="p-3 space-y-2">
          <div className="flex gap-2">
            <div className="rounded px-3 py-1 text-xs font-medium"
              style={{ backgroundColor: theme.primary, color: extractL(theme.primary) > 0.62 ? "#111" : "#fff" }}>
              Primary
            </div>
            <div className="rounded px-3 py-1 text-xs font-medium"
              style={{ backgroundColor: theme.accent, color: extractL(theme.accent) > 0.62 ? "#111" : "#fff" }}>
              Accent
            </div>
          </div>
          <div className="rounded-md p-3" style={{ backgroundColor: theme.card, border: `1px solid ${theme.border}` }}>
            <p className="text-xs mb-2" style={{ color: "oklch(0.93 0 0)" }}>Response card</p>
            <div className="flex gap-1">
              {theme.charts.map((c, i) => (
                <div key={i} className="flex-1 rounded" style={{ backgroundColor: c, height: `${30 + (5 - i) * 10}px` }} />
              ))}
            </div>
          </div>
          <div className="rounded px-2 py-1 text-xs" style={{ backgroundColor: theme.muted, color: "oklch(0.65 0 0)" }}>
            Muted section
          </div>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Full Genie Space mock preview
// ---------------------------------------------------------------------------

function GenieSpacePreview({ brand, theme }: { brand: BrandPalette; theme: DerivedTheme }) {
  const description = `Here's a breakdown of **revenue by region** for ${brand.name}:\n\n- **North America**: $4.2M (34%)\n- **Europe**: $3.1M (25%)\n- **Asia Pacific**: $2.8M (22%)\n- **Latin America**: $1.5M (12%)\n- **Middle East**: $0.9M (7%)\n\nNorth America remains the largest market, representing over a third of total revenue.`;

  const mdComponents = {
    p: ({ children }: { children?: React.ReactNode }) => <p className="mb-2 last:mb-0">{children}</p>,
    strong: ({ children }: { children?: React.ReactNode }) => <strong className="font-semibold">{children}</strong>,
    ul: ({ children }: { children?: React.ReactNode }) => <ul className="list-disc pl-5 mb-2 space-y-1">{children}</ul>,
    li: ({ children }: { children?: React.ReactNode }) => <li className="leading-relaxed">{children}</li>,
  };

  return (
    <div
      className="rounded-xl overflow-hidden border"
      style={{ backgroundColor: theme.background, borderColor: theme.border }}
    >
      {/* Sidebar + content layout */}
      <div className="flex">
        {/* Sidebar */}
        <div className="w-56 shrink-0 border-r flex flex-col" style={{ backgroundColor: tinted(extractH(theme.primary), 0.15, 0.03), borderColor: theme.border }}>
          <div className="h-1" style={{ backgroundColor: theme.primary }} />
          <div className="p-3">
            <div className="flex items-center gap-2 mb-4">
              <div className="w-8 h-8 rounded flex items-center justify-center text-white text-sm font-bold"
                style={{ backgroundColor: theme.primary }}>
                {brand.name.charAt(0)}
              </div>
              <span className="text-sm font-semibold" style={{ color: "oklch(0.93 0 0)" }}>{brand.name}</span>
            </div>
            {/* Nav items */}
            {["Home", "Chat", "Dashboard"].map((item) => (
              <div key={item} className="flex items-center gap-2 rounded px-2 py-1.5 mb-1 text-xs"
                style={{ color: item === "Chat" ? theme.primary : "oklch(0.65 0 0)", backgroundColor: item === "Chat" ? `${theme.primary}15` : "transparent" }}>
                <MessageSquare className="h-3 w-3" />
                {item}
              </div>
            ))}
            {/* Recent queries */}
            <p className="text-[10px] mt-4 mb-2 px-2 uppercase tracking-wider" style={{ color: "oklch(0.5 0 0)" }}>Recent</p>
            {["Revenue by region", "Top products"].map((q) => (
              <div key={q} className="rounded px-2 py-1.5 mb-1 text-xs cursor-pointer" style={{ color: "oklch(0.75 0 0)" }}>
                {q}
              </div>
            ))}
          </div>
        </div>

        {/* Main content */}
        <div className="flex-1 min-w-0 p-4 space-y-4">
          {/* Response card with markdown */}
          <div className="rounded-lg p-4" style={{ backgroundColor: theme.card, border: `1px solid ${theme.border}` }}>
            <div className="text-sm leading-relaxed" style={{ color: "oklch(0.93 0 0)" }}>
              <Markdown components={mdComponents}>{description}</Markdown>
            </div>
          </div>

          {/* Bar chart */}
          <div>
            <p className="text-[10px] font-medium uppercase tracking-wider mb-2" style={{ color: "oklch(0.5 0 0)" }}>Visualization</p>
            <div className="rounded-lg p-4" style={{ backgroundColor: theme.card, border: `1px solid ${theme.border}` }}>
              <p className="text-sm font-medium text-center mb-2" style={{ color: "oklch(0.85 0 0)" }}>Revenue by Region</p>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={MOCK_CHART_DATA}>
                  <CartesianGrid strokeDasharray="3 3" stroke={theme.border} opacity={0.5} />
                  <XAxis dataKey="category" tick={{ fontSize: 10, fill: "#ffffff" }}
                    tickFormatter={(v: string) => v.length > 12 ? v.slice(0, 10) + "…" : v} />
                  <YAxis tick={{ fontSize: 10, fill: "#ffffff" }}
                    tickFormatter={(v: number) => v >= 1000 ? `${(v / 1000).toFixed(1)}K` : String(v)} width={45} />
                  <Tooltip contentStyle={{ backgroundColor: theme.card, border: `1px solid ${theme.border}`, borderRadius: 8, color: "#fff" }} />
                  <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                    {MOCK_CHART_DATA.map((_, i) => (
                      <Cell key={i} fill={theme.charts[i % theme.charts.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Pie chart */}
          <div className="rounded-lg p-4" style={{ backgroundColor: theme.card, border: `1px solid ${theme.border}` }}>
            <p className="text-sm font-medium text-center mb-2" style={{ color: "oklch(0.85 0 0)" }}>Product Mix</p>
            <ResponsiveContainer width="100%" height={180}>
              <PieChart>
                <Pie data={MOCK_PIE_DATA} dataKey="value" nameKey="name" cx="50%" cy="50%"
                  outerRadius={70} innerRadius={35} paddingAngle={2}
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  labelLine={{ strokeWidth: 1 }}>
                  {MOCK_PIE_DATA.map((_, i) => (
                    <Cell key={i} fill={theme.charts[i % theme.charts.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ backgroundColor: theme.card, border: `1px solid ${theme.border}`, borderRadius: 8, color: "#fff" }} />
              </PieChart>
            </ResponsiveContainer>
          </div>

          {/* SQL toggle */}
          <div className="rounded-lg overflow-hidden" style={{ backgroundColor: theme.card, border: `1px solid ${theme.border}` }}>
            <div className="flex items-center gap-2 px-3 py-2 text-xs" style={{ color: "oklch(0.55 0 0)" }}>
              <ChevronRight className="h-3 w-3" />
              <Code2 className="h-3 w-3" />
              SQL Query
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

export function TestColorThemes() {
  const [selectedBrand, setSelectedBrand] = useState(0);
  const brand = BRANDS[selectedBrand];

  const currentTheme = deriveThemeCurrent(brand.primary, brand.accent, brand.chart_colors);
  const improvedTheme = deriveThemeImproved(brand.primary, brand.accent, brand.chart_colors);

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      {/* Brand selector */}
      <div className="flex items-center gap-3 flex-wrap">
        <span className="text-sm font-medium">Brand:</span>
        {BRANDS.map((b, i) => (
          <Button key={b.name} variant={selectedBrand === i ? "default" : "outline"} size="sm"
            onClick={() => setSelectedBrand(i)}>
            {b.name}
          </Button>
        ))}
      </div>

      {/* Raw palette */}
      <Card className="p-4">
        <p className="text-xs text-muted-foreground mb-2">LLM palette for <strong>{brand.name}</strong>:</p>
        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex items-center gap-1.5">
            <div className="w-5 h-5 rounded border" style={{ backgroundColor: brand.primary }} />
            <span className="text-xs font-mono">{brand.primary}</span>
            <span className="text-xs text-muted-foreground">primary</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-5 h-5 rounded border" style={{ backgroundColor: brand.accent }} />
            <span className="text-xs font-mono">{brand.accent}</span>
            <span className="text-xs text-muted-foreground">accent</span>
          </div>
          {brand.chart_colors.map((c, i) => (
            <div key={i} className="flex items-center gap-1">
              <div className="w-4 h-4 rounded border" style={{ backgroundColor: c }} />
              <span className="text-[10px] font-mono">{c}</span>
            </div>
          ))}
        </div>
      </Card>

      {/* Side-by-side small preview */}
      <div className="grid grid-cols-2 gap-6">
        <ThemePreview label="CURRENT" theme={currentTheme} />
        <ThemePreview label="IMPROVED (lightness spread)" theme={improvedTheme} />
      </div>

      {/* Full Genie Space mock — IMPROVED only */}
      <div>
        <p className="text-sm font-medium mb-3 flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-primary" />
          Mock Genie Space Preview (Improved Theme)
        </p>
        <GenieSpacePreview brand={brand} theme={improvedTheme} />
      </div>

      {/* Changes summary */}
      <Card className="p-4 text-xs space-y-1">
        <p className="font-medium mb-2">V2 Changes (lightness spread, not hue spread):</p>
        <p>Neutrals: deeper bg (0.13), less chroma (0.015) — cleaner, less muddy</p>
        <p>Primary/accent: +0.10 bump, 0.55 floor — always visible on dark bg</p>
        <p>Chart colors: 0.45 floor, then lightness redistribution if clustered (keeps brand hues)</p>
        <p>If all 5 chart colors are within 0.15 lightness range → spread to [0.65, 0.55, 0.75, 0.60, 0.70]</p>
      </Card>
    </div>
  );
}
