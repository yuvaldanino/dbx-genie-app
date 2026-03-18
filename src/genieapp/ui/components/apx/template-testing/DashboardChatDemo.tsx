/**
 * Template 2: Executive dashboard + inline chat split layout.
 * Left 2/3 has KPI cards with icons, gradient AreaChart, and styled table.
 * Right 1/3 is a premium chat panel with gradient border.
 */

import { MessageSquare, DollarSign, ShoppingCart, Store, Coffee } from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import {
  BRAND,
  KPIS,
  CHART_DATA,
  CHART_COLORS,
  TABLE_DATA,
  CHAT_MESSAGES,
  DRINK_CATEGORIES,
} from "./mock-data";
import { ChatMessageList, ChatInput } from "./ChatMessages";

const KPI_ICONS = {
  "dollar-sign": DollarSign,
  "shopping-cart": ShoppingCart,
  store: Store,
  coffee: Coffee,
} as const;

export function DashboardChatDemo() {
  return (
    <div className="flex w-full h-full rounded-xl overflow-hidden border">
      {/* Dashboard panel (2/3) */}
      <div
        className="flex-[2] overflow-y-auto p-6 space-y-5"
        style={{
          background: `radial-gradient(ellipse at 20% 50%, rgba(0,112,74,0.03), transparent 70%), ${BRAND.warmWhite}`,
        }}
      >
        {/* Header */}
        <div className="flex items-center gap-3">
          <img src={BRAND.logo} alt="Starbucks" className="h-8 w-8 object-contain" />
          <h2 className="text-lg font-bold" style={{ color: BRAND.secondary }}>
            Store Performance Dashboard
          </h2>
        </div>

        {/* KPI cards */}
        <div className="grid grid-cols-4 gap-3">
          {KPIS.map((kpi) => {
            const Icon = KPI_ICONS[kpi.icon as keyof typeof KPI_ICONS];
            return (
              <div
                key={kpi.label}
                className="rounded-lg p-3 bg-white shadow-sm border relative overflow-hidden transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md cursor-default"
              >
                <div className="absolute top-0 left-0 right-0 h-0.5" style={{ background: BRAND.primary }} />
                <div className="flex items-center justify-between mb-1">
                  <p className="text-[10px] text-gray-500 font-medium uppercase tracking-wide">
                    {kpi.label}
                  </p>
                  <div
                    className="w-6 h-6 rounded-full flex items-center justify-center"
                    style={{ background: BRAND.accent }}
                  >
                    <Icon className="h-3 w-3" style={{ color: BRAND.primary }} />
                  </div>
                </div>
                <p className="text-xl font-bold font-mono mt-1" style={{ color: BRAND.secondary }}>
                  {kpi.value}
                </p>
                <p className="text-xs mt-0.5 font-medium" style={{ color: BRAND.primary }}>
                  {kpi.delta}
                </p>
              </div>
            );
          })}
        </div>

        {/* Area chart with gradient fills */}
        <div className="bg-white rounded-lg shadow-sm border p-4">
          <h3 className="text-sm font-semibold mb-3" style={{ color: BRAND.secondary }}>
            Monthly Revenue by Category
          </h3>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={CHART_DATA}>
              <defs>
                {DRINK_CATEGORIES.map((cat, i) => (
                  <linearGradient key={cat} id={`dc-grad-${cat}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={CHART_COLORS[i]} stopOpacity={0.3} />
                    <stop offset="100%" stopColor={CHART_COLORS[i]} stopOpacity={0.02} />
                  </linearGradient>
                ))}
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
              <XAxis dataKey="month" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `$${v / 1000}k`} />
              <Tooltip formatter={(v: number) => `$${(v / 1000).toFixed(0)}k`} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              {DRINK_CATEGORIES.map((cat, i) => (
                <Area
                  key={cat}
                  type="monotone"
                  dataKey={cat}
                  stroke={CHART_COLORS[i]}
                  fill={`url(#dc-grad-${cat})`}
                  strokeWidth={2}
                  dot={false}
                />
              ))}
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Data table */}
        <div className="bg-white rounded-lg shadow-sm border overflow-hidden">
          <div className="px-4 py-3 border-b">
            <h3 className="text-sm font-semibold" style={{ color: BRAND.secondary }}>
              Top 10 Stores by Revenue
            </h3>
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr
                className="text-left text-xs text-gray-500 border-b sticky top-0"
                style={{ background: BRAND.accent }}
              >
                <th className="px-4 py-2 font-medium">Store</th>
                <th className="px-4 py-2 font-medium">City</th>
                <th className="px-4 py-2 font-medium">State</th>
                <th className="px-4 py-2 font-medium text-right">Revenue</th>
                <th className="px-4 py-2 font-medium text-right">Orders</th>
              </tr>
            </thead>
            <tbody>
              {TABLE_DATA.map((row, i) => (
                <tr
                  key={row.store}
                  className="transition-colors hover:bg-[rgba(0,112,74,0.03)]"
                  style={{ background: i % 2 === 0 ? "white" : "#FAFAF8" }}
                >
                  <td className="px-4 py-2 font-medium">{row.store}</td>
                  <td className="px-4 py-2 text-gray-600">{row.city}</td>
                  <td className="px-4 py-2 text-gray-600">{row.state}</td>
                  <td className="px-4 py-2 text-right font-mono">{row.revenue}</td>
                  <td className="px-4 py-2 text-right font-mono">{row.orders.toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Chat panel (1/3) */}
      <div className="flex-[1] flex flex-col bg-white relative">
        {/* Gradient left border */}
        <div
          className="absolute left-0 top-0 bottom-0 w-0.5"
          style={{ background: `linear-gradient(to bottom, ${BRAND.primary}, ${BRAND.accent})` }}
        />

        {/* Chat header */}
        <div
          className="px-4 py-3 flex items-center gap-2 text-white shrink-0"
          style={{
            background: `linear-gradient(135deg, ${BRAND.primary}, ${BRAND.secondary})`,
            backdropFilter: "blur(8px)",
          }}
        >
          <MessageSquare className="h-4 w-4" />
          <span className="font-semibold text-sm">Ask Genie</span>
        </div>

        <ChatMessageList messages={CHAT_MESSAGES} />
        <ChatInput />

        {/* Footer badge */}
        <div className="text-center py-2 border-t shrink-0">
          <span className="text-[10px] text-gray-400">Powered by Databricks Genie</span>
        </div>
      </div>
    </div>
  );
}
