/**
 * Template 5: Query Workspace — split layout with query sidebar and response viewer.
 * Left panel: Recent/Saved query tabs with pin/unpin. Right panel: response + visualization + SQL.
 */

import { useState, useMemo } from "react";
import { motion, AnimatePresence } from "motion/react";
import {
  Pin,
  PinOff,
  Filter,
  MoreHorizontal,
  ChevronDown,
  ChevronRight,
  Send,
  LayoutDashboard,
  FileDown,
  Database,
} from "lucide-react";
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
  CHAT_MESSAGES,
  CHART_DATA,
  CHART_COLORS,
  TABLE_DATA,
  DRINK_CATEGORIES,
} from "./mock-data";

/** Pair each user message with its following assistant response. */
interface QueryPair {
  query: string;
  response: (typeof CHAT_MESSAGES)[number];
  index: number;
}

function buildQueryPairs(): QueryPair[] {
  const pairs: QueryPair[] = [];
  for (let i = 0; i < CHAT_MESSAGES.length; i++) {
    const msg = CHAT_MESSAGES[i];
    if (msg.role === "user" && CHAT_MESSAGES[i + 1]?.role === "assistant") {
      pairs.push({ query: msg.content, response: CHAT_MESSAGES[i + 1], index: pairs.length });
    }
  }
  return pairs;
}

function FullChart() {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <AreaChart data={CHART_DATA}>
        <defs>
          {DRINK_CATEGORIES.map((cat, i) => (
            <linearGradient key={cat} id={`qw-grad-${cat}`} x1="0" y1="0" x2="0" y2="1">
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
            fill={`url(#qw-grad-${cat})`}
            strokeWidth={2}
            dot={false}
          />
        ))}
      </AreaChart>
    </ResponsiveContainer>
  );
}

function FullTable() {
  return (
    <div className="rounded-lg border overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-gray-500 border-b" style={{ background: BRAND.accent }}>
            <th className="px-4 py-2.5 font-medium">Store</th>
            <th className="px-4 py-2.5 font-medium">City</th>
            <th className="px-4 py-2.5 font-medium">State</th>
            <th className="px-4 py-2.5 font-medium text-right">Revenue</th>
            <th className="px-4 py-2.5 font-medium text-right">Orders</th>
          </tr>
        </thead>
        <tbody>
          {TABLE_DATA.map((row, i) => (
            <tr
              key={row.store}
              className={`transition-colors hover:bg-[rgba(0,112,74,0.03)] ${i % 2 === 0 ? "bg-white" : "bg-gray-50/50"}`}
            >
              <td className="px-4 py-2 font-medium">{row.store}</td>
              <td className="px-4 py-2 text-gray-600">{row.city}</td>
              <td className="px-4 py-2 text-gray-500">{row.state}</td>
              <td className="px-4 py-2 text-right font-mono">{row.revenue}</td>
              <td className="px-4 py-2 text-right font-mono text-gray-500">{row.orders.toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function QueryWorkspaceDemo() {
  const pairs = useMemo(buildQueryPairs, []);
  const [activeTab, setActiveTab] = useState<"recent" | "saved">("recent");
  const [savedIds, setSavedIds] = useState<Set<number>>(() => new Set([0, 2]));
  const [selectedIdx, setSelectedIdx] = useState(0);
  const [sqlExpanded, setSqlExpanded] = useState(false);
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);

  const toggleSaved = (idx: number) => {
    setSavedIds((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  };

  const visiblePairs =
    activeTab === "recent" ? pairs : pairs.filter((p) => savedIds.has(p.index));

  const selected = pairs[selectedIdx];

  return (
    <div
      className="flex h-full rounded-xl border overflow-hidden"
      style={{ background: BRAND.warmWhite }}
    >
      {/* Left: Query Sidebar */}
      <div className="w-[40%] flex flex-col border-r bg-white">
        {/* Tab switcher */}
        <div className="flex border-b shrink-0">
          {(["recent", "saved"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`flex-1 py-3 text-sm font-medium transition-colors cursor-pointer relative ${
                activeTab === tab
                  ? "text-gray-900"
                  : "text-gray-400 hover:text-gray-600"
              }`}
            >
              {tab === "recent" ? "Recent" : "Saved"}
              {tab === "saved" && savedIds.size > 0 && (
                <span
                  className="ml-1.5 text-[10px] px-1.5 py-0.5 rounded-full text-white"
                  style={{ background: BRAND.primary }}
                >
                  {savedIds.size}
                </span>
              )}
              {activeTab === tab && (
                <motion.div
                  layoutId="qw-tab-underline"
                  className="absolute bottom-0 left-0 right-0 h-0.5"
                  style={{ background: BRAND.primary }}
                  transition={{ type: "spring", damping: 25, stiffness: 300 }}
                />
              )}
            </button>
          ))}
        </div>

        {/* Query card list */}
        <div className="flex-1 overflow-y-auto p-3 space-y-2">
          <AnimatePresence mode="popLayout">
            {visiblePairs.map((pair) => {
              const isSelected = selectedIdx === pair.index;
              const isSaved = savedIds.has(pair.index);
              const isHovered = hoveredIdx === pair.index;
              return (
                <motion.div
                  key={pair.index}
                  layout
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  transition={{ duration: 0.2 }}
                  onClick={() => setSelectedIdx(pair.index)}
                  onMouseEnter={() => setHoveredIdx(pair.index)}
                  onMouseLeave={() => setHoveredIdx(null)}
                  className={`relative rounded-lg p-3 cursor-pointer transition-all border ${
                    isSelected
                      ? "border-[color:var(--sel-border)] shadow-sm"
                      : "border-transparent hover:border-gray-200"
                  }`}
                  style={
                    {
                      "--sel-border": BRAND.primary,
                      background: isSelected ? BRAND.accent : undefined,
                    } as React.CSSProperties
                  }
                >
                  <div className="flex items-start justify-between gap-2">
                    <p
                      className={`text-sm leading-snug ${
                        isSelected ? "font-medium" : ""
                      }`}
                      style={{ color: isSelected ? BRAND.secondary : "#374151" }}
                    >
                      {pair.query}
                    </p>

                    {/* Hover action pills */}
                    <AnimatePresence>
                      {(isHovered || isSelected) && (
                        <motion.div
                          initial={{ opacity: 0, scale: 0.8 }}
                          animate={{ opacity: 1, scale: 1 }}
                          exit={{ opacity: 0, scale: 0.8 }}
                          className="flex items-center gap-0.5 shrink-0"
                        >
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              toggleSaved(pair.index);
                            }}
                            className="p-1 rounded hover:bg-gray-100 transition-colors cursor-pointer"
                            title={isSaved ? "Unpin" : "Pin"}
                          >
                            {isSaved ? (
                              <PinOff className="h-3.5 w-3.5 text-gray-500" />
                            ) : (
                              <Pin className="h-3.5 w-3.5 text-gray-400" />
                            )}
                          </button>
                          <button className="p-1 rounded hover:bg-gray-100 transition-colors cursor-pointer">
                            <Filter className="h-3.5 w-3.5 text-gray-400" />
                          </button>
                          <button className="p-1 rounded hover:bg-gray-100 transition-colors cursor-pointer">
                            <MoreHorizontal className="h-3.5 w-3.5 text-gray-400" />
                          </button>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>

                  {/* Metadata */}
                  <div className="flex items-center gap-2 mt-1.5">
                    <span className="text-[10px] text-gray-400">
                      {pair.response.timestamp}
                    </span>
                    {pair.response.hasChart && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-50 text-blue-500">
                        Chart
                      </span>
                    )}
                    {pair.response.hasTable && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-50 text-amber-600">
                        Table
                      </span>
                    )}
                    {isSaved && (
                      <Pin className="h-3 w-3" style={{ color: BRAND.primary }} />
                    )}
                  </div>
                </motion.div>
              );
            })}
          </AnimatePresence>

          {activeTab === "saved" && visiblePairs.length === 0 && (
            <p className="text-sm text-gray-400 text-center py-8">
              No saved queries yet. Pin queries from the Recent tab.
            </p>
          )}
        </div>

        {/* Action buttons — only on Saved tab */}
        <AnimatePresence>
          {activeTab === "saved" && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="border-t p-3 flex gap-2 shrink-0"
            >
              {[
                { label: "Generate Dashboard", icon: LayoutDashboard },
                { label: "Export PDF", icon: FileDown },
                { label: "Save SQL Queries", icon: Database },
              ].map(({ label, icon: Icon }) => (
                <button
                  key={label}
                  className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs font-medium text-white transition-opacity hover:opacity-90 cursor-pointer"
                  style={{ background: BRAND.secondary }}
                >
                  <Icon className="h-3.5 w-3.5" />
                  {label}
                </button>
              ))}
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Right: Response Viewer */}
      <div className="flex-1 flex flex-col min-w-0">
        {selected ? (
          <>
            {/* Scrollable content */}
            <div className="flex-1 overflow-y-auto p-6 space-y-5">
              {/* Response text */}
              <div>
                <p className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-2">
                  Response
                </p>
                <p className="text-sm text-gray-700 leading-relaxed">
                  {selected.response.content}
                </p>
              </div>

              {/* Visualization */}
              {selected.response.hasChart && (
                <div className="bg-white rounded-lg border p-5">
                  <p className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-3">
                    Visualization
                  </p>
                  <FullChart />
                </div>
              )}

              {selected.response.hasTable && (
                <div>
                  <p className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-3">
                    Results
                  </p>
                  <FullTable />
                </div>
              )}

              {/* SQL Expander */}
              {selected.response.sql && (
                <div className="rounded-lg border overflow-hidden">
                  <button
                    onClick={() => setSqlExpanded(!sqlExpanded)}
                    className="w-full flex items-center gap-2 px-4 py-3 text-sm font-medium text-gray-600 hover:bg-gray-50 transition-colors cursor-pointer"
                  >
                    {sqlExpanded ? (
                      <ChevronDown className="h-4 w-4" />
                    ) : (
                      <ChevronRight className="h-4 w-4" />
                    )}
                    SQL Query
                  </button>
                  <AnimatePresence>
                    {sqlExpanded && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: "auto", opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.2 }}
                        className="overflow-hidden"
                      >
                        <pre className="text-xs bg-gray-900 text-green-400 p-4 overflow-x-auto whitespace-pre-wrap">
                          {selected.response.sql}
                        </pre>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              )}
            </div>

            {/* Chat input — bottom-pinned */}
            <div className="border-t p-3 flex gap-2 shrink-0">
              <input
                type="text"
                placeholder="Ask a follow-up question..."
                className="flex-1 text-sm rounded-full px-4 py-2 border focus:outline-none focus:ring-2"
                style={{ "--tw-ring-color": BRAND.primary } as React.CSSProperties}
                readOnly
              />
              <button
                className="rounded-full px-3 py-2 text-white cursor-pointer"
                style={{ background: `linear-gradient(135deg, ${BRAND.primary}, ${BRAND.secondary})` }}
              >
                <Send className="h-4 w-4" />
              </button>
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-gray-400 text-sm">
            Select a query to view its response
          </div>
        )}
      </div>
    </div>
  );
}
