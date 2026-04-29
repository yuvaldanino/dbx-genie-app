/**
 * Test scenarios — mock data + copied QueryResult with markdown fix.
 *
 * This file contains a COPY of QueryResult from QueryWorkspace.tsx.
 * The real app code is NOT modified. We iterate here, and if we like the
 * result, we apply the changes to the real component later.
 */

import { useState, type ReactNode } from "react";
import { TestLandingPage } from "./test-homepage";
import { TestSpacesPage } from "./test-spaces";
import { TestColorThemes } from "./test-color-themes";
import Markdown from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import { Card } from "@/components/ui/card";
import { TestChartRenderer } from "./test-chart-renderer";
import { DataTable } from "@/components/apx/DataTable";
import { Loader2, Code2, ChevronDown, ChevronRight } from "lucide-react";
import type { ChatMessageOut, ChartSuggestion } from "@/lib/api";

// ---------------------------------------------------------------------------
// Shared markdown component overrides (copied from MessageBubble.tsx:39-48)
// ---------------------------------------------------------------------------

const mdComponents = {
  h1: ({ children }: { children?: React.ReactNode }) => (
    <h1 className="text-lg font-semibold mb-2">{children}</h1>
  ),
  h2: ({ children }: { children?: React.ReactNode }) => (
    <h2 className="text-base font-semibold mb-2">{children}</h2>
  ),
  h3: ({ children }: { children?: React.ReactNode }) => (
    <h3 className="text-sm font-semibold mb-1">{children}</h3>
  ),
  p: ({ children }: { children?: React.ReactNode }) => (
    <p className="mb-2 last:mb-0">{children}</p>
  ),
  strong: ({ children }: { children?: React.ReactNode }) => (
    <strong className="font-semibold">{children}</strong>
  ),
  ul: ({ children }: { children?: React.ReactNode }) => (
    <ul className="list-disc pl-5 mb-2 space-y-1">{children}</ul>
  ),
  ol: ({ children }: { children?: React.ReactNode }) => (
    <ol className="list-decimal pl-5 mb-2 space-y-1">{children}</ol>
  ),
  li: ({ children }: { children?: React.ReactNode }) => (
    <li className="leading-relaxed">{children}</li>
  ),
  code: ({ children }: { children?: React.ReactNode }) => (
    <code className="bg-muted px-1.5 py-0.5 rounded text-xs font-mono">{children}</code>
  ),
};

// ---------------------------------------------------------------------------
// Message type (matches useChatFlow.ts)
// ---------------------------------------------------------------------------

interface Message {
  question: string;
  response?: ChatMessageOut;
  statusText?: string;
}

// ---------------------------------------------------------------------------
// TestQueryResult — COPY of QueryResult with markdown fix applied
// ---------------------------------------------------------------------------

function TestQueryResult({ msg }: { msg: Message }) {
  const [sqlExpanded, setSqlExpanded] = useState(false);

  if (!msg.response) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[300px]">
        <Loader2 className="h-8 w-8 animate-spin text-primary mb-3" />
        <p className="text-sm text-muted-foreground">
          {msg.statusText || "Processing..."}
        </p>
      </div>
    );
  }

  const r = msg.response;

  return (
    <div className="space-y-5 p-1">
      {/* ===== FIXED: Response description with markdown rendering ===== */}
      {r.description && (
        <Card className="p-5 bg-accent/5 border-accent/20 shadow-sm">
          <div className="text-sm leading-relaxed">
            <Markdown components={mdComponents}>{r.description}</Markdown>
          </div>
        </Card>
      )}

      {/* Error */}
      {r.error && (
        <Card className="p-3 border-destructive/30 bg-destructive/5 shadow-sm">
          <p className="text-sm text-destructive">{r.error}</p>
        </Card>
      )}

      {/* Chart */}
      {r.columns.length >= 2 && r.data.length > 0 && (
        <div>
          <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground mb-2">
            Visualization
          </p>
          <Card className="p-4 shadow-sm">
            <TestChartRenderer
              key={r.message_id || "chart"}
              suggestion={
                r.chart_suggestion && r.chart_suggestion.chart_type !== "table"
                  ? r.chart_suggestion
                  : {
                      chart_type: "bar",
                      x_axis: r.columns[0],
                      y_axis: r.columns[1],
                      title: "",
                    }
              }
              data={r.data}
              columns={r.columns}
            />
          </Card>
        </div>
      )}

      {/* Table */}
      {r.columns.length > 0 && r.data.length > 0 && (
        <div>
          <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground mb-2">
            Results
            {r.row_count > 0 && (
              <span className="ml-2 text-muted-foreground/60 normal-case tracking-normal">
                {r.row_count} row{r.row_count !== 1 ? "s" : ""}
              </span>
            )}
          </p>
          <Card className="overflow-hidden shadow-sm">
            <DataTable columns={r.columns} data={r.data} className="max-h-80" />
          </Card>
        </div>
      )}

      {/* SQL */}
      {r.sql && (
        <Card className="overflow-hidden">
          <button
            className="w-full flex items-center gap-2 px-4 py-2.5 text-xs text-muted-foreground hover:bg-muted/50 transition-colors"
            onClick={() => setSqlExpanded(!sqlExpanded)}
          >
            {sqlExpanded ? (
              <ChevronDown className="h-3 w-3" />
            ) : (
              <ChevronRight className="h-3 w-3" />
            )}
            <Code2 className="h-3 w-3" />
            SQL Query
          </button>
          {sqlExpanded && (
            <SyntaxHighlighter
              language="sql"
              style={oneDark}
              customStyle={{
                margin: 0,
                borderRadius: 0,
                fontSize: "0.75rem",
                padding: "0.75rem",
              }}
              wrapLongLines
            >
              {r.sql}
            </SyntaxHighlighter>
          )}
        </Card>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Mock data — realistic Genie responses
// ---------------------------------------------------------------------------

let mockCounter = 0;
function mockResponse(overrides: Partial<ChatMessageOut>): ChatMessageOut {
  mockCounter++;
  return {
    conversation_id: "test-conv-1",
    message_id: `test-msg-${mockCounter}`,
    status: "COMPLETED",
    description: "",
    sql: "",
    columns: [],
    data: [],
    row_count: 0,
    chart_suggestion: null,
    error: null,
    suggested_questions: [],
    query_description: "",
    is_truncated: false,
    is_clarification: false,
    error_type: "",
    ...overrides,
  };
}

// Scenario 1: The exact broken case the user reported
const depositBalanceResponse = mockResponse({
  description:
    'The total deposit balance by account type is as follows:\n\n- **Savings:** $51,422.80\n- **Checking:** $18,111.33\n- **Certificate of Deposit:** $50,000.00\n- **Money Market:** $22,450.89\n\nThe highest total deposit balance is in **Savings** accounts, while **Checking** accounts have the lowest among the listed types.',
  sql: "SELECT account_type, SUM(balance) as total_balance\nFROM deposits\nGROUP BY account_type\nORDER BY total_balance DESC",
  columns: ["account_type", "total_balance"],
  data: [
    { account_type: "Savings", total_balance: 51422.8 },
    { account_type: "Certificate of Deposit", total_balance: 50000.0 },
    { account_type: "Money Market", total_balance: 22450.89 },
    { account_type: "Checking", total_balance: 18111.33 },
  ],
  row_count: 4,
  chart_suggestion: {
    chart_type: "bar",
    x_axis: "account_type",
    y_axis: "total_balance",
    title: "Total Deposit Balance by Account Type",
  },
});

// Scenario 2: Revenue analysis with rich markdown
const revenueAnalysisResponse = mockResponse({
  description:
    "Here's a breakdown of **total revenue by region** for Q1 2026:\n\n- **North America**: $4.2M (+12% YoY)\n- **Europe**: $3.1M (+8% YoY)\n- **Asia Pacific**: $2.8M (+22% YoY)\n- **Latin America**: $1.5M (+5% YoY)\n\nKey takeaways:\n\n1. **Asia Pacific** is the fastest-growing region, driven by expansion in Southeast Asian markets\n2. **North America** remains the largest revenue contributor at 36% of total\n3. Combined revenue of **$11.6M** represents a **13% increase** over Q1 2025",
  sql: "SELECT region, SUM(revenue) as total_revenue,\n  ROUND((SUM(revenue) - LAG(SUM(revenue)) OVER (ORDER BY region)) / LAG(SUM(revenue)) OVER (ORDER BY region) * 100, 1) as yoy_growth\nFROM sales\nWHERE quarter = 'Q1' AND year = 2026\nGROUP BY region\nORDER BY total_revenue DESC",
  columns: ["region", "total_revenue"],
  data: [
    { region: "North America", total_revenue: 4200000 },
    { region: "Europe", total_revenue: 3100000 },
    { region: "Asia Pacific", total_revenue: 2800000 },
    { region: "Latin America", total_revenue: 1500000 },
  ],
  row_count: 4,
  chart_suggestion: {
    chart_type: "bar",
    x_axis: "region",
    y_axis: "total_revenue",
    title: "Revenue by Region - Q1 2026",
  },
});

// Scenario 3: Forkable meal orders (from our actual test data)
const forkableOrdersResponse = mockResponse({
  description:
    "The meal order distribution by type shows:\n\n- **Lunch** dominates with **269 orders** (67.3% of total)\n- **Dinner** accounts for **85 orders** (21.3%)\n- **Breakfast** has **46 orders** (11.5%)\n\nThe average order total is **$18.70**, with lunch orders averaging slightly higher due to more premium restaurant selections. **Delivered** orders make up 91.3% of all orders, with only 6% cancelled and 2.8% refunded.",
  sql: "SELECT meal_type, COUNT(*) as order_count, ROUND(AVG(order_total), 2) as avg_total\nFROM meal_orders\nGROUP BY meal_type\nORDER BY order_count DESC",
  columns: ["meal_type", "order_count", "avg_total"],
  data: [
    { meal_type: "lunch", order_count: 269, avg_total: 19.2 },
    { meal_type: "dinner", order_count: 85, avg_total: 18.5 },
    { meal_type: "breakfast", order_count: 46, avg_total: 15.8 },
  ],
  row_count: 3,
  chart_suggestion: {
    chart_type: "pie",
    x_axis: "meal_type",
    y_axis: "order_count",
    title: "Meal Orders by Type",
  },
});

// Scenario 4: Error state
const errorResponse = mockResponse({
  description: "",
  error: "The query could not be completed. The table `transactions` does not exist in the current schema. Available tables: deposits, accounts, customers, loans.",
  error_type: "NOT_FOUND",
});

// Scenario 5: KPI / single-value response
const kpiResponse = mockResponse({
  description:
    "The **total active users** across all corporate clients is **42,500**. This represents an **85% activation rate** from the 50,000 registered employees.\n\nOf these active users:\n- **38,200** placed at least one order in the last 30 days\n- **28,750** are weekly recurring orderers\n- **4,300** have been inactive for 30+ days but haven't churned",
  sql: "SELECT COUNT(*) as active_users FROM employees WHERE is_active = 1",
  columns: ["active_users"],
  data: [{ active_users: 42500 }],
  row_count: 1,
  chart_suggestion: {
    chart_type: "kpi",
    x_axis: null,
    y_axis: "active_users",
    title: "Total Active Users",
  },
});

// Scenario 6: Long multi-section response
const longDescriptionResponse = mockResponse({
  description:
    "## Restaurant Performance Analysis\n\nBased on the analysis of delivery times and ratings across all 20 partner restaurants:\n\n**Top Performers:**\n- **Sweetgreen Downtown** — 4.8 avg rating, 15 min avg delivery\n- **Cava Midtown** — 4.7 avg rating, 18 min avg delivery\n- **Shake Shack Financial District** — 4.6 avg rating, 20 min avg delivery\n\n**Areas for Improvement:**\n- **Panda Express Union Square** — 3.8 avg rating, 32 min avg delivery\n- **Subway Times Square** — 3.9 avg rating, 28 min avg delivery\n\n**Correlation:** There is a strong negative correlation (`r = -0.78`) between delivery time and customer rating. Restaurants with delivery times under 20 minutes average **4.5+ stars**, while those over 25 minutes average **under 4.0 stars**.\n\n**Recommendation:** Focus delivery optimization efforts on the 5 restaurants with delivery times exceeding 25 minutes. A 5-minute reduction in delivery time is associated with approximately **0.3-point rating improvement**.",
  sql: "SELECT r.restaurant_name, ROUND(AVG(m.rating), 1) as avg_rating,\n  ROUND(AVG(m.delivery_time_minutes), 0) as avg_delivery_min\nFROM meal_orders m\nJOIN restaurants r ON m.restaurant_id = r.restaurant_id\nGROUP BY r.restaurant_name\nORDER BY avg_rating DESC",
  columns: ["restaurant_name", "avg_rating", "avg_delivery_min"],
  data: [
    { restaurant_name: "Sweetgreen Downtown", avg_rating: 4.8, avg_delivery_min: 15 },
    { restaurant_name: "Cava Midtown", avg_rating: 4.7, avg_delivery_min: 18 },
    { restaurant_name: "Shake Shack Financial District", avg_rating: 4.6, avg_delivery_min: 20 },
    { restaurant_name: "Chipotle Market St", avg_rating: 4.4, avg_delivery_min: 22 },
    { restaurant_name: "Just Salad Flatiron", avg_rating: 4.2, avg_delivery_min: 24 },
    { restaurant_name: "Subway Times Square", avg_rating: 3.9, avg_delivery_min: 28 },
    { restaurant_name: "Panda Express Union Square", avg_rating: 3.8, avg_delivery_min: 32 },
  ],
  row_count: 7,
  chart_suggestion: {
    chart_type: "bar",
    x_axis: "restaurant_name",
    y_axis: "avg_rating",
    title: "Restaurant Performance: Rating vs Delivery Time",
  },
});

// Scenario 7: Loading state (no response yet)
const loadingMessage: Message = {
  question: "What is the total revenue by product category?",
  statusText: "Generating SQL...",
};

// ---------------------------------------------------------------------------
// Scenario definitions
// ---------------------------------------------------------------------------

export interface Scenario {
  name: string;
  description: string;
  render: () => ReactNode;
}

export const scenarios: Scenario[] = [
  {
    name: "Deposit Balance (Original Bug)",
    description: "The exact response that looked bad — markdown now renders properly",
    render: () => (
      <TestQueryResult
        msg={{
          question: "What is the total deposit balance by account type?",
          response: depositBalanceResponse,
        }}
      />
    ),
  },
  {
    name: "Revenue Analysis (Rich Markdown)",
    description: "Multi-paragraph with numbered lists and bold highlights",
    render: () => (
      <TestQueryResult
        msg={{
          question: "Show me total revenue by region for Q1 2026",
          response: revenueAnalysisResponse,
        }}
      />
    ),
  },
  {
    name: "Forkable Meal Orders",
    description: "Pie chart with percentage breakdown",
    render: () => (
      <TestQueryResult
        msg={{
          question: "How are meal orders distributed by type?",
          response: forkableOrdersResponse,
        }}
      />
    ),
  },
  {
    name: "Error State",
    description: "Table not found error",
    render: () => (
      <TestQueryResult
        msg={{
          question: "Show me all transactions from last month",
          response: errorResponse,
        }}
      />
    ),
  },
  {
    name: "KPI Single Value",
    description: "Single metric with rich context description",
    render: () => (
      <TestQueryResult
        msg={{
          question: "How many active users do we have?",
          response: kpiResponse,
        }}
      />
    ),
  },
  {
    name: "Long Description (Restaurant Analysis)",
    description: "Multi-section with headers, correlation stats, recommendations",
    render: () => (
      <TestQueryResult
        msg={{
          question: "Analyze restaurant performance by delivery time and rating",
          response: longDescriptionResponse,
        }}
      />
    ),
  },
  {
    name: "Loading State",
    description: "No response yet — shows spinner",
    render: () => <TestQueryResult msg={loadingMessage} />,
  },
  {
    name: "Homepage (Create Space Form)",
    description: "Wider layout, 2-column grid, logged-in-as indicator",
    render: () => <TestLandingPage />,
  },
  {
    name: "Spaces Page",
    description: "No Connect Existing button, logged-in-as indicator, mock spaces",
    render: () => <TestSpacesPage />,
  },
  {
    name: "Color Themes (Side-by-Side)",
    description: "Current vs improved color derivation for Nike, Forkable, Starbucks, etc.",
    render: () => <TestColorThemes />,
  },
];
