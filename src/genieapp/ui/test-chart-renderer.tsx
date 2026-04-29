/**
 * Improved ChartRenderer — sandbox copy with better formatting.
 *
 * Changes vs original ChartRenderer.tsx:
 * 1. Human-readable column names (total_balance → Total Balance)
 * 2. Abbreviated Y-axis ticks (45000 → 45K)
 * 3. Custom tooltip with clean layout and proper formatting
 * 4. Angled X-axis labels for long text
 * 5. Better tooltip dark-mode styling
 * 6. Improved legend formatting
 */

import { useState } from "react";
import {
  BarChart3,
  LineChart as LineChartIcon,
  PieChart as PieChartIcon,
  AreaChart as AreaChartIcon,
  Hash,
  MapPin,
} from "lucide-react";
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  Legend,
} from "recharts";
import { Button } from "@/components/ui/button";
import type { ChartSuggestion } from "@/lib/api";

// ---------------------------------------------------------------------------
// Colors
// ---------------------------------------------------------------------------

const COLORS = [
  "var(--chart-1)",
  "var(--chart-2)",
  "var(--chart-3)",
  "var(--chart-4)",
  "var(--chart-5)",
  "#8884d8",
  "#82ca9d",
];

const CHART_TYPES = [
  { type: "bar", icon: BarChart3, label: "Bar" },
  { type: "line", icon: LineChartIcon, label: "Line" },
  { type: "area", icon: AreaChartIcon, label: "Area" },
  { type: "pie", icon: PieChartIcon, label: "Pie" },
  { type: "kpi", icon: Hash, label: "KPI" },
  { type: "map", icon: MapPin, label: "Map" },
] as const;

type ChartType = (typeof CHART_TYPES)[number]["type"];

interface ChartRendererProps {
  suggestion: ChartSuggestion;
  data: Record<string, string | number | null>[];
  columns: string[];
}

// ---------------------------------------------------------------------------
// Formatting helpers
// ---------------------------------------------------------------------------

/** Convert column_name → "Column Name" */
function formatColumnName(col: string): string {
  return col
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

/** Abbreviate large numbers for axis ticks: 1500 → 1.5K, 2000000 → 2M */
function formatAxisTick(value: number | string): string {
  const num = Number(value);
  if (isNaN(num)) return String(value);
  const abs = Math.abs(num);
  const sign = num < 0 ? "-" : "";
  if (abs >= 1_000_000_000) return `${sign}${(abs / 1_000_000_000).toFixed(abs >= 10_000_000_000 ? 0 : 1)}B`;
  if (abs >= 1_000_000) return `${sign}${(abs / 1_000_000).toFixed(abs >= 10_000_000 ? 0 : 1)}M`;
  if (abs >= 1_000) return `${sign}${(abs / 1_000).toFixed(abs >= 10_000 ? 0 : 1)}K`;
  if (abs % 1 !== 0) return num.toFixed(2);
  return num.toLocaleString();
}

/** Format value for tooltip display — full precision with commas */
function formatTooltipValue(value: number | string): string {
  const num = Number(value);
  if (isNaN(num)) return String(value);
  if (Number.isInteger(num)) return num.toLocaleString();
  return num.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

/** KPI big number */
function formatKpiValue(value: number): string {
  const abs = Math.abs(value);
  const sign = value < 0 ? "-" : "";
  if (abs >= 1_000_000_000) return `${sign}${(abs / 1_000_000_000).toFixed(1)}B`;
  if (abs >= 1_000_000) return `${sign}${(abs / 1_000_000).toFixed(1)}M`;
  if (abs >= 1_000) return `${sign}${(abs / 1_000).toFixed(1)}K`;
  if (abs % 1 !== 0) return value.toFixed(2);
  return value.toLocaleString();
}

function coerceNumeric(data: Record<string, unknown>[], yAxis: string) {
  return data.map((row) => ({
    ...row,
    [yAxis]: Number(row[yAxis]) || 0,
  }));
}

const ID_SUFFIXES = ["_id", "_key", "_pk", "_fk", "_code"];

function isIdColumn(col: string): boolean {
  const lower = col.toLowerCase();
  if (lower === "id") return true;
  return ID_SUFFIXES.some((s) => lower.endsWith(s));
}

function isNumericColumn(data: Record<string, unknown>[], col: string): boolean {
  if (isIdColumn(col)) return false;
  const sample = data.slice(0, 10).filter((row) => row[col] !== null && row[col] !== "");
  if (sample.length === 0) return false;
  const numericCount = sample.filter((row) => !isNaN(Number(row[col]))).length;
  return numericCount > sample.length / 2;
}

/** Check if any x-axis value is long enough to need angled labels */
function needsAngledLabels(data: Record<string, unknown>[], xAxis: string): boolean {
  return data.some((row) => String(row[xAxis] ?? "").length > 10);
}

// ---------------------------------------------------------------------------
// Custom Tooltip
// ---------------------------------------------------------------------------

interface TooltipPayloadItem {
  value: number | string;
  dataKey: string;
  color: string;
  payload: Record<string, unknown>;
}

function CustomTooltip({
  active,
  payload,
  label,
  xAxis,
}: {
  active?: boolean;
  payload?: TooltipPayloadItem[];
  label?: string;
  xAxis: string;
}) {
  if (!active || !payload || payload.length === 0) return null;

  return (
    <div className="rounded-lg border border-border/80 bg-card px-3 py-2.5 shadow-xl text-card-foreground">
      <p className="text-sm font-medium mb-1">{String(label)}</p>
      {payload.map((entry, i) => (
        <div key={i} className="flex items-center gap-2 text-sm">
          <span
            className="inline-block h-2.5 w-2.5 rounded-full shrink-0"
            style={{ backgroundColor: entry.color }}
          />
          <span className="text-muted-foreground">{formatColumnName(entry.dataKey)}:</span>
          <span className="font-medium">{formatTooltipValue(entry.value)}</span>
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export function TestChartRenderer({ suggestion, data, columns }: ChartRendererProps) {
  const numericCols = columns.filter((c) => isNumericColumn(data, c));
  const [chartType, setChartType] = useState<ChartType>(suggestion.chart_type as ChartType);
  const [xAxis, setXAxis] = useState(() => {
    return suggestion.x_axis && columns.includes(suggestion.x_axis) ? suggestion.x_axis : columns[0];
  });
  const [yAxis, setYAxis] = useState(() => {
    if (suggestion.y_axis && numericCols.includes(suggestion.y_axis)) return suggestion.y_axis;
    return numericCols[0] || columns[1] || columns[0];
  });

  if (!data.length) return null;
  const chartData = yAxis ? coerceNumeric(data, yAxis) : data;
  const angledLabels = needsAngledLabels(data, xAxis);

  // KPI — single large number
  if (chartType === "kpi") {
    const value = data[0]?.[yAxis || columns[0]];
    const label = suggestion.title || formatColumnName(yAxis || columns[0]);
    return (
      <div className="space-y-2">
        <ChartToolbar
          chartType={chartType}
          onTypeChange={setChartType}
          columns={columns}
          numericCols={numericCols}
          xAxis={xAxis}
          yAxis={yAxis}
          onXChange={setXAxis}
          onYChange={setYAxis}
        />
        <div className="flex flex-col items-center justify-center py-8 w-full overflow-hidden">
          <p className="text-sm text-muted-foreground text-center break-words max-w-full">{label}</p>
          <p className="text-5xl font-bold mt-2 text-center break-all max-w-full">
            {(() => {
              const num = Number(value);
              if (value != null && !isNaN(num)) return formatKpiValue(num);
              return String(value ?? "—");
            })()}
          </p>
        </div>
      </div>
    );
  }

  // Shared axis props
  const xAxisProps = {
    dataKey: xAxis,
    tick: { fontSize: 11, fill: "#ffffff" },
    tickFormatter: (v: string) => (v.length > 18 ? v.slice(0, 16) + "…" : v),
    ...(angledLabels
      ? { angle: -35, textAnchor: "end" as const, height: 80, interval: 0 }
      : {}),
  };

  const yAxisProps = {
    tick: { fontSize: 11, fill: "#ffffff" },
    tickFormatter: formatAxisTick,
    width: 55,
  };

  return (
    <div className="w-full max-w-full space-y-2 overflow-hidden" id="chart-container">
      <ChartToolbar
        chartType={chartType}
        onTypeChange={setChartType}
        columns={columns}
        numericCols={numericCols}
        xAxis={xAxis}
        yAxis={yAxis}
        onXChange={setXAxis}
        onYChange={setYAxis}
      />
      {suggestion.title && (
        <p className="text-sm font-medium text-center">{suggestion.title}</p>
      )}
      <ResponsiveContainer width="100%" height={angledLabels ? 340 : 300}>
        {chartType === "bar" ? (
          <BarChart data={chartData} margin={angledLabels ? { bottom: 20 } : undefined}>
            <CartesianGrid strokeDasharray="3 3" className="opacity-20" />
            <XAxis {...xAxisProps} />
            <YAxis {...yAxisProps} />
            <Tooltip content={<CustomTooltip xAxis={xAxis} />} cursor={{ fill: "var(--muted)", opacity: 0.3 }} />
            <Legend formatter={(value: string) => formatColumnName(value)} wrapperStyle={{ fontSize: 12 }} />
            <Bar dataKey={yAxis} fill="var(--chart-1)" radius={[4, 4, 0, 0]} />
          </BarChart>
        ) : chartType === "line" ? (
          <LineChart data={chartData} margin={angledLabels ? { bottom: 20 } : undefined}>
            <CartesianGrid strokeDasharray="3 3" className="opacity-20" />
            <XAxis {...xAxisProps} />
            <YAxis {...yAxisProps} />
            <Tooltip content={<CustomTooltip xAxis={xAxis} />} />
            <Legend formatter={(value: string) => formatColumnName(value)} wrapperStyle={{ fontSize: 12 }} />
            <Line type="monotone" dataKey={yAxis} stroke="var(--chart-1)" strokeWidth={2} dot={{ r: 3 }} />
          </LineChart>
        ) : chartType === "area" ? (
          <AreaChart data={chartData} margin={angledLabels ? { bottom: 20 } : undefined}>
            <CartesianGrid strokeDasharray="3 3" className="opacity-20" />
            <XAxis {...xAxisProps} />
            <YAxis {...yAxisProps} />
            <Tooltip content={<CustomTooltip xAxis={xAxis} />} />
            <Legend formatter={(value: string) => formatColumnName(value)} wrapperStyle={{ fontSize: 12 }} />
            <Area type="monotone" dataKey={yAxis} stroke="var(--chart-1)" fill="var(--chart-1)" fillOpacity={0.2} />
          </AreaChart>
        ) : chartType === "pie" ? (
          <PieChart>
            <Pie
              data={chartData}
              dataKey={yAxis}
              nameKey={xAxis}
              cx="50%"
              cy="50%"
              outerRadius={90}
              innerRadius={40}
              paddingAngle={2}
              label={({ name, percent }) =>
                `${String(name).length > 15 ? String(name).slice(0, 13) + "…" : name} ${(percent * 100).toFixed(0)}%`
              }
              labelLine={{ strokeWidth: 1 }}
            >
              {chartData.map((_, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip
              formatter={(v: number | string, name: string) => [formatTooltipValue(v), String(name)]}
            />
            <Legend
              wrapperStyle={{ fontSize: 12, maxWidth: "100%", overflow: "hidden" }}
              layout="horizontal"
              align="center"
            />
          </PieChart>
        ) : (
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" className="opacity-20" />
            <XAxis {...xAxisProps} />
            <YAxis {...yAxisProps} />
            <Tooltip content={<CustomTooltip xAxis={xAxis} />} cursor={{ fill: "var(--muted)", opacity: 0.3 }} />
            <Bar dataKey={yAxis} fill="var(--chart-1)" radius={[4, 4, 0, 0]} />
          </BarChart>
        )}
      </ResponsiveContainer>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Toolbar
// ---------------------------------------------------------------------------

function ChartToolbar({
  chartType,
  onTypeChange,
  columns,
  numericCols,
  xAxis,
  yAxis,
  onXChange,
  onYChange,
}: {
  chartType: ChartType;
  onTypeChange: (t: ChartType) => void;
  columns: string[];
  numericCols: string[];
  xAxis: string;
  yAxis: string;
  onXChange: (col: string) => void;
  onYChange: (col: string) => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-2 text-xs w-full max-w-full overflow-hidden">
      {/* Chart type buttons */}
      <div className="flex items-center border rounded-md overflow-hidden shrink-0">
        {CHART_TYPES.map(({ type, icon: Icon, label }) => (
          <Button
            key={type}
            variant={chartType === type ? "secondary" : "ghost"}
            size="sm"
            className="h-7 px-2 rounded-none gap-1"
            onClick={() => onTypeChange(type)}
            title={label}
          >
            <Icon className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">{label}</span>
          </Button>
        ))}
      </div>

      {/* Axis selectors — show formatted column names */}
      <div className="flex items-center gap-1.5 min-w-0 overflow-hidden">
        <label className="text-muted-foreground">X:</label>
        <select
          className="h-7 px-1.5 rounded border bg-background text-xs max-w-[140px] truncate"
          value={xAxis}
          onChange={(e) => onXChange(e.target.value)}
        >
          {columns.map((col) => (
            <option key={col} value={col}>
              {formatColumnName(col)}
            </option>
          ))}
        </select>

        <label className="text-muted-foreground ml-1">Y:</label>
        <select
          className="h-7 px-1.5 rounded border bg-background text-xs max-w-[140px] truncate"
          value={yAxis}
          onChange={(e) => onYChange(e.target.value)}
        >
          {numericCols.map((col) => (
            <option key={col} value={col}>
              {formatColumnName(col)}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
