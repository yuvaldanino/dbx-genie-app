/**
 * Template 2: Dashboard + inline chat split layout.
 * Left 2/3 has KPI cards, bar chart, and data table. Right 1/3 is a chat panel.
 */

import { MessageSquare, Send } from "lucide-react";
import {
  BarChart,
  Bar,
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
} from "./mock-data";

export function DashboardChatDemo() {
  return (
    <div className="flex w-full h-[700px] rounded-xl overflow-hidden border">
      {/* Dashboard panel (2/3) */}
      <div className="flex-[2] bg-gray-50 overflow-y-auto p-6 space-y-6">
        {/* Header */}
        <div className="flex items-center gap-3">
          <img src={BRAND.logo} alt="Starbucks" className="h-8 w-8 object-contain" />
          <h2 className="text-lg font-bold" style={{ color: BRAND.secondary }}>
            Store Performance Dashboard
          </h2>
        </div>

        {/* KPI cards */}
        <div className="grid grid-cols-4 gap-3">
          {KPIS.map((kpi) => (
            <div key={kpi.label} className="rounded-lg p-3 bg-white shadow-sm border">
              <p className="text-[10px] text-gray-500 font-medium uppercase tracking-wide">
                {kpi.label}
              </p>
              <p className="text-xl font-bold mt-1" style={{ color: BRAND.secondary }}>
                {kpi.value}
              </p>
              <p className="text-xs mt-0.5" style={{ color: BRAND.primary }}>
                {kpi.delta}
              </p>
            </div>
          ))}
        </div>

        {/* Bar chart */}
        <div className="bg-white rounded-lg shadow-sm border p-4">
          <h3 className="text-sm font-semibold mb-3" style={{ color: BRAND.secondary }}>
            Monthly Revenue by Category
          </h3>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={CHART_DATA}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
              <XAxis dataKey="month" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `$${v / 1000}k`} />
              <Tooltip formatter={(v: number) => `$${(v / 1000).toFixed(0)}k`} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              {["Espresso", "Frappuccino", "Tea", "ColdBrew", "Refreshers"].map(
                (key, i) => (
                  <Bar key={key} dataKey={key} fill={CHART_COLORS[i]} radius={[2, 2, 0, 0]} />
                )
              )}
            </BarChart>
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
              <tr className="text-left text-xs text-gray-500 border-b" style={{ background: BRAND.accent }}>
                <th className="px-4 py-2 font-medium">Store</th>
                <th className="px-4 py-2 font-medium">City</th>
                <th className="px-4 py-2 font-medium">State</th>
                <th className="px-4 py-2 font-medium text-right">Revenue</th>
                <th className="px-4 py-2 font-medium text-right">Orders</th>
              </tr>
            </thead>
            <tbody>
              {TABLE_DATA.map((row, i) => (
                <tr key={row.store} className={i % 2 === 0 ? "bg-white" : "bg-gray-50"}>
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
      <div className="flex-[1] border-l flex flex-col bg-white">
        {/* Chat header */}
        <div
          className="px-4 py-3 flex items-center gap-2 text-white shrink-0"
          style={{ background: BRAND.primary }}
        >
          <MessageSquare className="h-4 w-4" />
          <span className="font-semibold text-sm">Ask Genie</span>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {CHAT_MESSAGES.map((msg, i) => (
            <div
              key={i}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[85%] rounded-lg px-3 py-2 text-sm ${
                  msg.role === "user" ? "text-white" : "bg-gray-100 text-gray-800"
                }`}
                style={msg.role === "user" ? { background: BRAND.primary } : undefined}
              >
                <p>{msg.content}</p>
                {msg.sql && (
                  <pre className="mt-2 text-[10px] bg-gray-900 text-green-400 rounded p-2 overflow-x-auto whitespace-pre-wrap">
                    {msg.sql}
                  </pre>
                )}
                {msg.hasTable && (
                  <div className="mt-2 text-[10px] rounded p-2 border text-gray-500 bg-gray-50">
                    📊 [Table: Top 5 stores by revenue]
                  </div>
                )}
                {msg.hasChart && (
                  <div className="mt-2 text-[10px] rounded p-2 border text-gray-500 bg-gray-50">
                    📈 [Chart: Monthly revenue by category]
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Input */}
        <div className="border-t p-3 flex gap-2 shrink-0">
          <input
            type="text"
            placeholder="Ask a question..."
            className="flex-1 text-sm border rounded-lg px-3 py-2 focus:outline-none focus:ring-2"
            readOnly
          />
          <button
            className="rounded-lg px-3 py-2 text-white"
            style={{ background: BRAND.primary }}
          >
            <Send className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
