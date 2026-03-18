/**
 * Template 1: Floating chat widget on a premium Starbucks dashboard background.
 * Click bubble to expand chat panel with avatars, timestamps, typing indicator.
 */

import { useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { MessageSquare, X, DollarSign, ShoppingCart, Store, Coffee } from "lucide-react";
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

export function FloatingWidgetDemo() {
  const [open, setOpen] = useState(false);

  return (
    <div className="relative w-full h-full rounded-xl overflow-hidden border" style={{ background: BRAND.warmWhite }}>
      {/* Mock dashboard background */}
      <div className="p-6 space-y-5 overflow-y-auto h-full pb-24">
        <div className="flex items-center gap-3">
          <img src={BRAND.logo} alt="Starbucks" className="h-10 w-10 object-contain" />
          <h2 className="text-xl font-bold" style={{ color: BRAND.secondary }}>
            Starbucks Analytics
          </h2>
        </div>

        {/* KPI cards */}
        <div className="grid grid-cols-4 gap-4">
          {KPIS.map((kpi) => {
            const Icon = KPI_ICONS[kpi.icon as keyof typeof KPI_ICONS];
            return (
              <div
                key={kpi.label}
                className="rounded-lg p-4 bg-white shadow-sm border relative overflow-hidden transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md cursor-default"
              >
                <div className="absolute top-0 left-0 right-0 h-0.5" style={{ background: BRAND.primary }} />
                <div className="flex items-center justify-between mb-1">
                  <p className="text-xs text-gray-500 font-medium">{kpi.label}</p>
                  <div
                    className="w-7 h-7 rounded-full flex items-center justify-center"
                    style={{ background: BRAND.accent }}
                  >
                    <Icon className="h-3.5 w-3.5" style={{ color: BRAND.primary }} />
                  </div>
                </div>
                <p className="text-2xl font-bold font-mono" style={{ color: BRAND.secondary }}>
                  {kpi.value}
                </p>
                <p className="text-xs mt-1 font-medium" style={{ color: BRAND.primary }}>
                  {kpi.delta}
                </p>
              </div>
            );
          })}
        </div>

        {/* Real AreaChart */}
        <div className="bg-white rounded-lg shadow-sm border p-5">
          <h3 className="text-sm font-semibold mb-3" style={{ color: BRAND.secondary }}>
            Monthly Revenue by Category
          </h3>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={CHART_DATA}>
              <defs>
                {DRINK_CATEGORIES.map((cat, i) => (
                  <linearGradient key={cat} id={`fw-grad-${cat}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={CHART_COLORS[i]} stopOpacity={0.25} />
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
                  fill={`url(#fw-grad-${cat})`}
                  strokeWidth={2}
                  dot={false}
                />
              ))}
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Real mini data table — top 5 stores */}
        <div className="bg-white rounded-lg shadow-sm border overflow-hidden">
          <div className="px-4 py-3 border-b">
            <h3 className="text-sm font-semibold" style={{ color: BRAND.secondary }}>
              Top Stores by Revenue
            </h3>
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-gray-500 border-b" style={{ background: BRAND.accent }}>
                <th className="px-4 py-2 font-medium">Store</th>
                <th className="px-4 py-2 font-medium">City</th>
                <th className="px-4 py-2 font-medium text-right">Revenue</th>
                <th className="px-4 py-2 font-medium text-right">Orders</th>
              </tr>
            </thead>
            <tbody>
              {TABLE_DATA.slice(0, 5).map((row, i) => (
                <tr
                  key={row.store}
                  className={`transition-colors hover:bg-[rgba(0,112,74,0.03)] ${i % 2 === 0 ? "bg-white" : "bg-gray-50/50"}`}
                >
                  <td className="px-4 py-2 font-medium">{row.store}</td>
                  <td className="px-4 py-2 text-gray-600">{row.city}</td>
                  <td className="px-4 py-2 text-right font-mono">{row.revenue}</td>
                  <td className="px-4 py-2 text-right font-mono text-gray-500">{row.orders.toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Chat bubble */}
      <AnimatePresence>
        {!open && (
          <motion.button
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            exit={{ scale: 0 }}
            whileHover={{ scale: 1.1 }}
            onClick={() => setOpen(true)}
            className="absolute bottom-6 right-6 w-14 h-14 rounded-full flex items-center justify-center text-white cursor-pointer"
            style={{
              background: `linear-gradient(135deg, ${BRAND.primary}, ${BRAND.secondary})`,
              boxShadow: "0 4px 24px rgba(0,112,74,0.4)",
            }}
          >
            <MessageSquare className="h-6 w-6" />
          </motion.button>
        )}
      </AnimatePresence>

      {/* Chat panel */}
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.95 }}
            transition={{ type: "spring", damping: 25, stiffness: 300 }}
            className="absolute bottom-6 right-6 w-96 h-[520px] bg-white rounded-xl flex flex-col overflow-hidden"
            style={{
              border: "1px solid rgba(255,255,255,0.2)",
              boxShadow: "0 8px 40px rgba(0,0,0,0.12)",
            }}
          >
            {/* Header */}
            <div
              className="px-4 py-3 flex items-center justify-between text-white shrink-0"
              style={{ background: `linear-gradient(135deg, ${BRAND.primary}, ${BRAND.secondary})` }}
            >
              <div className="flex items-center gap-2">
                <MessageSquare className="h-4 w-4" />
                <span className="font-semibold text-sm">Ask Genie</span>
              </div>
              <button onClick={() => setOpen(false)} className="hover:opacity-80 cursor-pointer">
                <X className="h-4 w-4" />
              </button>
            </div>

            <ChatMessageList messages={CHAT_MESSAGES} />
            <ChatInput />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
