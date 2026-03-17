/**
 * Template 1: Floating chat widget on a mock Starbucks dashboard background.
 * Click bubble to expand chat panel with hardcoded messages.
 */

import { useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { MessageSquare, X, Send } from "lucide-react";
import { BRAND, KPIS, CHAT_MESSAGES } from "./mock-data";

export function FloatingWidgetDemo() {
  const [open, setOpen] = useState(false);

  return (
    <div className="relative w-full h-[700px] rounded-xl overflow-hidden border" style={{ background: "#f7f5f2" }}>
      {/* Mock dashboard background */}
      <div className="p-6 space-y-6">
        <div className="flex items-center gap-3">
          <img src={BRAND.logo} alt="Starbucks" className="h-10 w-10 object-contain" />
          <h2 className="text-xl font-bold" style={{ color: BRAND.secondary }}>
            Starbucks Analytics
          </h2>
        </div>

        {/* Mock KPI row */}
        <div className="grid grid-cols-4 gap-4">
          {KPIS.map((kpi) => (
            <div
              key={kpi.label}
              className="rounded-lg p-4 bg-white shadow-sm border"
            >
              <p className="text-xs text-gray-500 font-medium">{kpi.label}</p>
              <p className="text-2xl font-bold mt-1" style={{ color: BRAND.secondary }}>
                {kpi.value}
              </p>
              <p className="text-xs mt-1" style={{ color: BRAND.primary }}>
                {kpi.delta}
              </p>
            </div>
          ))}
        </div>

        {/* Mock chart placeholder */}
        <div className="bg-white rounded-lg shadow-sm border p-6 h-48 flex items-center justify-center">
          <p className="text-gray-400 text-sm">Monthly Revenue Chart Area</p>
        </div>

        {/* Mock table placeholder */}
        <div className="bg-white rounded-lg shadow-sm border p-6 h-32 flex items-center justify-center">
          <p className="text-gray-400 text-sm">Store Performance Table Area</p>
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
            className="absolute bottom-6 right-6 w-14 h-14 rounded-full shadow-lg flex items-center justify-center text-white cursor-pointer"
            style={{ background: BRAND.primary }}
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
            className="absolute bottom-6 right-6 w-96 h-[500px] bg-white rounded-xl shadow-2xl border flex flex-col overflow-hidden"
          >
            {/* Header */}
            <div
              className="px-4 py-3 flex items-center justify-between text-white shrink-0"
              style={{ background: BRAND.primary }}
            >
              <div className="flex items-center gap-2">
                <MessageSquare className="h-4 w-4" />
                <span className="font-semibold text-sm">Ask Genie</span>
              </div>
              <button onClick={() => setOpen(false)} className="hover:opacity-80 cursor-pointer">
                <X className="h-4 w-4" />
              </button>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {CHAT_MESSAGES.map((msg, i) => (
                <div
                  key={i}
                  className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-[80%] rounded-lg px-3 py-2 text-sm ${
                      msg.role === "user"
                        ? "text-white"
                        : "bg-gray-100 text-gray-800"
                    }`}
                    style={msg.role === "user" ? { background: BRAND.primary } : undefined}
                  >
                    <p>{msg.content}</p>
                    {msg.sql && (
                      <pre className="mt-2 text-[10px] bg-gray-900 text-green-400 rounded p-2 overflow-x-auto">
                        {msg.sql}
                      </pre>
                    )}
                    {msg.hasTable && (
                      <div className="mt-2 text-[10px] bg-gray-50 rounded p-2 border text-gray-500">
                        📊 [Table: Top 5 stores by revenue]
                      </div>
                    )}
                    {msg.hasChart && (
                      <div className="mt-2 text-[10px] bg-gray-50 rounded p-2 border text-gray-500">
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
                style={{ focusRingColor: BRAND.primary } as React.CSSProperties}
                readOnly
              />
              <button
                className="rounded-lg px-3 py-2 text-white"
                style={{ background: BRAND.primary }}
              >
                <Send className="h-4 w-4" />
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
