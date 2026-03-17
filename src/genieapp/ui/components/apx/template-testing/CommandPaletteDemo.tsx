/**
 * Template 3: Command palette / spotlight search.
 * Centered search bar. Focus opens modal with query result (chart + table).
 * Previous results shown as cards below.
 */

import { useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { Search, X, BarChart3, Table2 } from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { BRAND, CHART_DATA, CHART_COLORS, TABLE_DATA, CHAT_MESSAGES } from "./mock-data";

export function CommandPaletteDemo() {
  const [modalOpen, setModalOpen] = useState(false);

  return (
    <div className="w-full h-[700px] rounded-xl overflow-hidden border bg-gray-50 flex flex-col">
      {/* Header */}
      <div className="p-6 pb-0 flex items-center gap-3">
        <img src={BRAND.logo} alt="Starbucks" className="h-8 w-8 object-contain" />
        <h2 className="text-lg font-bold" style={{ color: BRAND.secondary }}>
          Starbucks Intelligence
        </h2>
      </div>

      {/* Search bar */}
      <div className="px-6 py-8 flex justify-center">
        <button
          onClick={() => setModalOpen(true)}
          className="w-full max-w-2xl flex items-center gap-3 px-5 py-4 bg-white rounded-xl shadow-md border hover:shadow-lg transition-shadow cursor-pointer text-left"
        >
          <Search className="h-5 w-5 text-gray-400" />
          <span className="text-gray-400 text-base">
            Ask anything about your data...
          </span>
          <kbd className="ml-auto text-xs text-gray-400 border rounded px-2 py-0.5 bg-gray-50">
            &#8984;K
          </kbd>
        </button>
      </div>

      {/* Previous results cards */}
      <div className="px-6 flex-1 overflow-y-auto">
        <p className="text-xs text-gray-500 font-medium uppercase tracking-wide mb-3">
          Recent Queries
        </p>
        <div className="grid grid-cols-2 gap-4">
          {CHAT_MESSAGES.filter((m) => m.role === "assistant").map((msg, i) => (
            <button
              key={i}
              onClick={() => setModalOpen(true)}
              className="bg-white rounded-lg shadow-sm border p-4 text-left hover:shadow-md transition-shadow cursor-pointer"
            >
              <div className="flex items-center gap-2 mb-2">
                {msg.hasChart ? (
                  <BarChart3 className="h-4 w-4" style={{ color: BRAND.primary }} />
                ) : (
                  <Table2 className="h-4 w-4" style={{ color: BRAND.primary }} />
                )}
                <span className="text-xs font-medium text-gray-500">
                  {msg.hasChart ? "Chart Result" : "Table Result"}
                </span>
              </div>
              <p className="text-sm text-gray-800 line-clamp-2">{msg.content}</p>
              {msg.sql && (
                <pre className="mt-2 text-[9px] bg-gray-900 text-green-400 rounded p-2 overflow-hidden line-clamp-2">
                  {msg.sql}
                </pre>
              )}
            </button>
          ))}
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
              className="absolute inset-0 bg-black/40 z-40"
            />
            <motion.div
              initial={{ opacity: 0, y: -20, scale: 0.97 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -20, scale: 0.97 }}
              transition={{ type: "spring", damping: 25, stiffness: 300 }}
              className="absolute inset-x-0 top-12 mx-auto w-full max-w-3xl bg-white rounded-xl shadow-2xl border z-50 overflow-hidden"
            >
              {/* Search input in modal */}
              <div className="flex items-center gap-3 px-5 py-4 border-b">
                <Search className="h-5 w-5 text-gray-400" />
                <span className="flex-1 text-sm text-gray-800">
                  Show me monthly revenue by drink category
                </span>
                <button
                  onClick={() => setModalOpen(false)}
                  className="text-gray-400 hover:text-gray-600 cursor-pointer"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              {/* Result content */}
              <div className="p-5 space-y-4 max-h-[500px] overflow-y-auto">
                <p className="text-sm text-gray-700">
                  Monthly revenue breakdown by drink category shows Espresso consistently
                  leading, with Frappuccino sales picking up in warmer months.
                </p>

                {/* Chart */}
                <div className="bg-gray-50 rounded-lg p-4 border">
                  <ResponsiveContainer width="100%" height={200}>
                    <BarChart data={CHART_DATA}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
                      <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                      <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `$${v / 1000}k`} />
                      <Tooltip formatter={(v: number) => `$${(v / 1000).toFixed(0)}k`} />
                      {["Espresso", "Frappuccino", "Tea", "ColdBrew", "Refreshers"].map(
                        (key, i) => (
                          <Bar key={key} dataKey={key} fill={CHART_COLORS[i]} radius={[2, 2, 0, 0]} />
                        )
                      )}
                    </BarChart>
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
                        <tr key={row.store} className={i % 2 === 0 ? "bg-white" : "bg-gray-50"}>
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

                {/* SQL */}
                <pre className="text-[10px] bg-gray-900 text-green-400 rounded-lg p-3 overflow-x-auto">
{`SELECT DATE_TRUNC('month', order_date) as month,
       drink_category,
       SUM(revenue) as total_revenue
FROM starbucks.sales.transactions
GROUP BY month, drink_category
ORDER BY month, total_revenue DESC`}
                </pre>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}
