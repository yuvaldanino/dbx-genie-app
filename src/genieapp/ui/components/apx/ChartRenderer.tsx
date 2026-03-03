/**
 * Interactive Recharts visualizations with chart type + axis controls.
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
import { MapRenderer } from "./MapRenderer";
import type { ChartSuggestion } from "@/lib/api";

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

function coerceNumeric(data: Record<string, unknown>[], yAxis: string) {
  return data.map((row) => ({
    ...row,
    [yAxis]: Number(row[yAxis]) || 0,
  }));
}

function isNumericColumn(data: Record<string, unknown>[], col: string): boolean {
  const sample = data.slice(0, 10);
  return sample.some((row) => !isNaN(Number(row[col])) && row[col] !== null && row[col] !== "");
}

export function ChartRenderer({ suggestion, data, columns }: ChartRendererProps) {
  const [chartType, setChartType] = useState<ChartType>(suggestion.chart_type as ChartType);
  const [xAxis, setXAxis] = useState(suggestion.x_axis || columns[0]);
  const [yAxis, setYAxis] = useState(suggestion.y_axis || columns[1] || columns[0]);

  if (!data.length) return null;

  const numericCols = columns.filter((c) => isNumericColumn(data, c));
  const chartData = yAxis ? coerceNumeric(data, yAxis) : data;

  // Map — lat/lon markers
  if (chartType === "map") {
    // x_axis = lon column, y_axis = lat column, title = label column
    const latCol = yAxis || columns.find((c) => /^lat/i.test(c)) || columns[0];
    const lonCol = xAxis || columns.find((c) => /^lo?n/i.test(c)) || columns[1];
    const labelCol = suggestion.title && columns.includes(suggestion.title) ? suggestion.title : undefined;
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
        <MapRenderer
          data={data}
          latColumn={latCol}
          lonColumn={lonCol}
          labelColumn={labelCol}
          columns={columns}
        />
      </div>
    );
  }

  // KPI — single large number
  if (chartType === "kpi") {
    const value = data[0]?.[yAxis || columns[0]];
    const label = suggestion.title || yAxis || columns[0];
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
        <div className="flex flex-col items-center justify-center py-8">
          <p className="text-sm text-muted-foreground">{label}</p>
          <p className="text-5xl font-bold mt-2">
            {typeof value === "number"
              ? value.toLocaleString()
              : String(value ?? "—")}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full space-y-2" id="chart-container">
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
      <ResponsiveContainer width="100%" height={300}>
        {chartType === "bar" ? (
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
            <XAxis dataKey={xAxis} tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip />
            <Legend />
            <Bar dataKey={yAxis} fill="var(--chart-1)" radius={[4, 4, 0, 0]} />
          </BarChart>
        ) : chartType === "line" ? (
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
            <XAxis dataKey={xAxis} tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey={yAxis} stroke="var(--chart-1)" strokeWidth={2} dot={{ r: 3 }} />
          </LineChart>
        ) : chartType === "area" ? (
          <AreaChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
            <XAxis dataKey={xAxis} tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip />
            <Legend />
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
              outerRadius={100}
              label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
            >
              {chartData.map((_, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip />
            <Legend />
          </PieChart>
        ) : (
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey={xAxis} />
            <YAxis />
            <Tooltip />
            <Bar dataKey={yAxis} fill="var(--chart-1)" />
          </BarChart>
        )}
      </ResponsiveContainer>
    </div>
  );
}

/** Toolbar for switching chart type and selecting axes. */
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
    <div className="flex flex-wrap items-center gap-2 text-xs">
      {/* Chart type buttons */}
      <div className="flex items-center border rounded-md overflow-hidden">
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

      {/* Axis selectors */}
      <div className="flex items-center gap-1.5 ml-auto">
        <label className="text-muted-foreground">X:</label>
        <select
          className="h-7 px-1.5 rounded border bg-background text-xs"
          value={xAxis}
          onChange={(e) => onXChange(e.target.value)}
        >
          {columns.map((col) => (
            <option key={col} value={col}>{col}</option>
          ))}
        </select>

        <label className="text-muted-foreground ml-1">Y:</label>
        <select
          className="h-7 px-1.5 rounded border bg-background text-xs"
          value={yAxis}
          onChange={(e) => onYChange(e.target.value)}
        >
          {numericCols.map((col) => (
            <option key={col} value={col}>{col}</option>
          ))}
        </select>
      </div>
    </div>
  );
}
