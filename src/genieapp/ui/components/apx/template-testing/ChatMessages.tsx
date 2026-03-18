/**
 * Shared chat message renderer with avatars, timestamps, typing indicator,
 * inline mini-previews, and pill-shaped input bar. Used by FloatingWidget and DashboardChat.
 */

import { motion } from "motion/react";
import { Send, Sparkles } from "lucide-react";
import { Area, AreaChart, ResponsiveContainer } from "recharts";
import { BRAND, CHART_DATA, CHART_COLORS, TABLE_DATA, type ChatMessage } from "./mock-data";

interface ChatMessagesProps {
  messages: ChatMessage[];
  showTyping?: boolean;
}

function UserAvatar() {
  return (
    <div
      className="w-7 h-7 rounded-full flex items-center justify-center text-[10px] font-bold text-white shrink-0"
      style={{ background: BRAND.secondary }}
    >
      YD
    </div>
  );
}

function AssistantAvatar() {
  return (
    <div
      className="w-7 h-7 rounded-full flex items-center justify-center shrink-0"
      style={{ background: BRAND.accent }}
    >
      <Sparkles className="h-3.5 w-3.5" style={{ color: BRAND.primary }} />
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="flex items-end gap-2">
      <AssistantAvatar />
      <div className="bg-gray-100 rounded-2xl rounded-bl-md px-4 py-2.5 flex gap-1">
        {[0, 1, 2].map((i) => (
          <motion.span
            key={i}
            className="w-1.5 h-1.5 rounded-full bg-gray-400"
            animate={{ y: [0, -4, 0] }}
            transition={{ duration: 0.6, repeat: Infinity, delay: i * 0.15 }}
          />
        ))}
      </div>
    </div>
  );
}

function MiniChart() {
  return (
    <div className="mt-2 rounded-md border bg-white/80 p-1.5">
      <ResponsiveContainer width="100%" height={50}>
        <AreaChart data={CHART_DATA}>
          <Area
            type="monotone"
            dataKey="Espresso"
            stroke={CHART_COLORS[0]}
            fill={CHART_COLORS[0]}
            fillOpacity={0.15}
            strokeWidth={1.5}
            dot={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

function MiniTable() {
  return (
    <div className="mt-2 rounded-md border bg-white/80 overflow-hidden">
      <table className="w-full text-[9px]">
        <tbody>
          {TABLE_DATA.slice(0, 3).map((row) => (
            <tr key={row.store} className="border-b last:border-0">
              <td className="px-2 py-1 font-medium text-gray-700">{row.store}</td>
              <td className="px-2 py-1 text-right font-mono text-gray-500">{row.revenue}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function ChatMessageList({ messages, showTyping = true }: ChatMessagesProps) {
  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-3">
      {messages.map((msg, i) => (
        <motion.div
          key={i}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.1, duration: 0.3 }}
          className={`flex gap-2 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
        >
          {msg.role === "assistant" && <AssistantAvatar />}
          <div className="flex flex-col gap-0.5 max-w-[80%]">
            <div
              className={`px-3 py-2 text-sm ${
                msg.role === "user"
                  ? "rounded-2xl rounded-br-md text-white"
                  : "rounded-2xl rounded-bl-md bg-gray-100 text-gray-800"
              }`}
              style={msg.role === "user" ? { background: BRAND.primary } : undefined}
            >
              <p>{msg.content}</p>
              {msg.sql && (
                <pre className="mt-2 text-[10px] bg-gray-900 text-green-400 rounded p-2 overflow-x-auto whitespace-pre-wrap">
                  {msg.sql}
                </pre>
              )}
              {msg.hasTable && <MiniTable />}
              {msg.hasChart && <MiniChart />}
            </div>
            <span className="text-[10px] text-gray-400 px-1">
              {msg.timestamp}
            </span>
          </div>
          {msg.role === "user" && <UserAvatar />}
        </motion.div>
      ))}
      {showTyping && <TypingIndicator />}
    </div>
  );
}

export function ChatInput() {
  return (
    <div className="border-t p-3 flex gap-2 shrink-0">
      <input
        type="text"
        placeholder="Ask a question..."
        className="flex-1 text-sm rounded-full px-4 py-2 border focus:outline-none focus:ring-2"
        style={{ "--tw-ring-color": BRAND.primary } as React.CSSProperties}
        readOnly
      />
      <button
        className="rounded-full px-3 py-2 text-white"
        style={{ background: `linear-gradient(135deg, ${BRAND.primary}, ${BRAND.secondary})` }}
      >
        <Send className="h-4 w-4" />
      </button>
    </div>
  );
}
