/**
 * Template 3: Command palette / spotlight search — Raycast/Linear-inspired.
 * Centered search bar with suggestion pills, blurred backdrop modal,
 * category tabs, gradient AreaChart, and refined styling.
 */

import { useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import {
  Search,
  X,
  BarChart3,
  Table2,
  DollarSign,
  Store,
  Coffee,
  TrendingUp,
  Copy,
} from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import {
  BRAND,
  CHART_DATA,
  CHART_COLORS,
  TABLE_DATA,
  CHAT_MESSAGES,
  SUGGESTED_QUERIES,
  DRINK_CATEGORIES,
} from "./mock-data";

const SUGGESTION_ICONS = {
  "dollar-sign": DollarSign,
  store: Store,
  coffee: Coffee,
  "trending-up": TrendingUp,
} as const;

const CATEGORY_TABS = ["All", "Charts", "Tables", "SQL"] as const;

export function CommandPaletteDemo() {
  const [modalOpen, setModalOpen] = useState(false);
  const [activeCategory, setActiveCategory] = useState<string>("All");

  const assistantMessages = CHAT_MESSAGES.filter((m) => m.role === "assistant");

  return (
    <div
      className="w-full h-full rounded-xl overflow-hidden border flex flex-col"
      style={{
        background: `radial-gradient(ellipse at 50% 0%, rgba(0,112,74,0.04), transparent 60%), ${BRAND.warmWhite}`,
      }}
    >
      {/* Header */}
      <div className="p-6 pb-0 flex items-center gap-3">
        <img src={BRAND.logo} alt="Starbucks" className="h-8 w-8 object-contain" />
        <h2 className="text-lg font-bold" style={{ color: BRAND.secondary }}>
          Starbucks Intelligence
        </h2>
      </div>

      {/* Search bar */}
      <div className="px-6 pt-8 pb-4 flex justify-center">
        <button
          onClick={() => setModalOpen(true)}
          className="w-full max-w-2xl flex items-center gap-3 px-5 py-4 bg-white rounded-xl shadow-lg border hover:shadow-xl transition-shadow cursor-pointer text-left"
          style={{ borderLeft: `2px solid ${BRAND.primary}` }}
        >
          <Search className="h-5 w-5" style={{ color: BRAND.primary }} />
          <span className="text-gray-400 text-base">
            Ask anything about your data...
          </span>
          <kbd className="ml-auto text-xs text-gray-400 border rounded px-2 py-0.5 bg-gray-50">
            &#8984;K
          </kbd>
        </button>
      </div>

      {/* Suggestion pills */}
      <div className="px-6 flex justify-center pb-6">
        <div className="flex gap-2 flex-wrap max-w-2xl w-full">
          {SUGGESTED_QUERIES.map((sq) => {
            const Icon = SUGGESTION_ICONS[sq.icon as keyof typeof SUGGESTION_ICONS];
            return (
              <button
                key={sq.query}
                onClick={() => setModalOpen(true)}
                className="flex items-center gap-1.5 rounded-full bg-white border px-3 py-1.5 text-xs text-gray-600 hover:border-[rgba(0,112,74,0.3)] hover:bg-[rgba(0,112,74,0.05)] transition-colors cursor-pointer"
              >
                <Icon className="h-3 w-3" style={{ color: BRAND.primary }} />
                {sq.query}
              </button>
            );
          })}
        </div>
      </div>

      {/* Recent query cards */}
      <div className="px-6 flex-1 overflow-y-auto">
        <p className="text-xs text-gray-500 font-medium uppercase tracking-wide mb-3">
          Recent Queries
        </p>
        <div className="grid grid-cols-2 gap-4">
          {assistantMessages.map((msg, i) => {
            const userMsg = CHAT_MESSAGES[i * 2];
            return (
              <button
                key={i}
                onClick={() => setModalOpen(true)}
                className="bg-white rounded-lg shadow-sm border p-4 text-left transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md cursor-pointer"
              >
                <div className="flex items-center gap-2 mb-2">
                  <div
                    className="w-6 h-6 rounded-full flex items-center justify-center"
                    style={{ background: BRAND.accent }}
                  >
                    {msg.hasChart ? (
                      <BarChart3 className="h-3 w-3" style={{ color: BRAND.primary }} />
                    ) : (
                      <Table2 className="h-3 w-3" style={{ color: BRAND.primary }} />
                    )}
                  </div>
                  <span className="text-xs font-medium text-gray-500">
                    {msg.hasChart ? "Chart" : "Table"}
                  </span>
                  <span className="ml-auto text-[10px] text-gray-400">{msg.timestamp}</span>
                </div>
                <p className="text-xs text-gray-400 mb-1 truncate">{userMsg?.content}</p>
                <p className="text-sm text-gray-800 line-clamp-2">{msg.content}</p>
                {msg.sql && (
                  <pre className="mt-2 text-[9px] bg-gray-900 text-green-400 rounded p-2 overflow-hidden line-clamp-2">
                    {msg.sql}
                  </pre>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Modal overlay */}
      <AnimatePresence>
        {modalOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setModalOpen(false)}
              className="absolute inset-0 z-40"
              style={{ background: "rgba(0,0,0,0.3)", backdropFilter: "blur(8px)" }}
            />
            <motion.div
              initial={{ opacity: 0, y: -20, scale: 0.97 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -20, scale: 0.97 }}
              transition={{ type: "spring", damping: 22, stiffness: 400 }}
              className="absolute inset-x-0 top-12 mx-auto w-full max-w-3xl rounded-xl z-50 overflow-hidden"
              style={{
                background: "rgba(255,255,255,0.95)",
                backdropFilter: "blur(12px)",
                boxShadow: "0 24px 80px rgba(0,0,0,0.15)",
                border: "1px solid rgba(255,255,255,0.6)",
              }}
            >
              {/* Search input in modal */}
              <div className="flex items-center gap-3 px-5 py-4 border-b">
                <div style={{ borderLeft: `2px solid ${BRAND.primary}`, paddingLeft: 8 }} className="flex items-center gap-3 flex-1">
                  <Search className="h-5 w-5" style={{ color: BRAND.primary }} />
                  <span className="flex-1 text-sm text-gray-800">
                    Show me monthly revenue by drink category
                  </span>
                </div>
                <button
                  onClick={() => setModalOpen(false)}
                  className="text-gray-400 hover:text-gray-600 cursor-pointer"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              {/* Category tabs */}
              <div className="flex gap-1 px-5 py-2 border-b bg-gray-50/50">
                {CATEGORY_TABS.map((cat) => (
                  <button
                    key={cat}
                    onClick={() => setActiveCategory(cat)}
                    className={`px-3 py-1 rounded-full text-xs font-medium transition-colors cursor-pointer ${
                      activeCategory === cat
                        ? "text-white"
                        : "text-gray-500 hover:text-gray-700 hover:bg-gray-100"
                    }`}
                    style={activeCategory === cat ? { background: BRAND.primary } : undefined}
                  >
                    {cat}
                  </button>
                ))}
              </div>

              {/* Result content */}
              <div className="p-5 space-y-4 max-h-[460px] overflow-y-auto">
                <p className="text-sm text-gray-700">
                  Monthly revenue breakdown by drink category shows Espresso consistently
                  leading, with Frappuccino sales picking up in warmer months.
                </p>

                {/* AreaChart with gradient fills */}
                <div className="bg-gray-50/80 rounded-lg p-4 border">
                  <ResponsiveContainer width="100%" height={200}>
                    <AreaChart data={CHART_DATA}>
                      <defs>
                        {DRINK_CATEGORIES.map((cat, i) => (
                          <linearGradient key={cat} id={`cp-grad-${cat}`} x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor={CHART_COLORS[i]} stopOpacity={0.3} />
                            <stop offset="100%" stopColor={CHART_COLORS[i]} stopOpacity={0.02} />
                          </linearGradient>
                        ))}
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
                      <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                      <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `$${v / 1000}k`} />
                      <Tooltip formatter={(v: number) => `$${(v / 1000).toFixed(0)}k`} />
                      {DRINK_CATEGORIES.map((cat, i) => (
                        <Area
                          key={cat}
                          type="monotone"
                          dataKey={cat}
                          stroke={CHART_COLORS[i]}
                          fill={`url(#cp-grad-${cat})`}
                          strokeWidth={2}
                          dot={false}
                        />
                      ))}
                    </AreaChart>
                  </ResponsiveContainer>
                </div>

                {/* Table */}
                <div className="rounded-lg border overflow-hidden">
                  <table className="w-full text-sm">
                    <thead>
                      <tr
                        className="text-left text-xs text-gray-500 border-b"
                        style={{ background: BRAND.accent }}
                      >
                        <th className="px-3 py-2 font-medium">Store</th>
                        <th className="px-3 py-2 font-medium">City</th>
                        <th className="px-3 py-2 font-medium">State</th>
                        <th className="px-3 py-2 font-medium text-right">Revenue</th>
                        <th className="px-3 py-2 font-medium text-right">Orders</th>
                      </tr>
                    </thead>
                    <tbody>
                      {TABLE_DATA.slice(0, 5).map((row, i) => (
                        <tr
                          key={row.store}
                          className="transition-colors hover:bg-[rgba(0,112,74,0.03)]"
                          style={{ background: i % 2 === 0 ? "white" : "#FAFAF8" }}
                        >
                          <td className="px-3 py-1.5 font-medium">{row.store}</td>
                          <td className="px-3 py-1.5 text-gray-600">{row.city}</td>
                          <td className="px-3 py-1.5 text-gray-600">{row.state}</td>
                          <td className="px-3 py-1.5 text-right font-mono">{row.revenue}</td>
                          <td className="px-3 py-1.5 text-right font-mono">
                            {row.orders.toLocaleString()}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* SQL with label + copy button */}
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-[10px] font-medium text-gray-500 uppercase tracking-wide">
                      Generated SQL
                    </span>
                    <button className="flex items-center gap-1 text-[10px] text-gray-400 hover:text-gray-600 cursor-pointer">
                      <Copy className="h-3 w-3" />
                      Copy
                    </button>
                  </div>
                  <pre className="text-[10px] bg-gray-900 text-green-400 rounded-lg p-3 overflow-x-auto">
{`SELECT DATE_TRUNC('month', order_date) as month,
       drink_category,
       SUM(revenue) as total_revenue
FROM starbucks.sales.transactions
GROUP BY month, drink_category
ORDER BY month, total_revenue DESC`}
                  </pre>
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}
