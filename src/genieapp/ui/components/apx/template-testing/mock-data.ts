/**
 * Hardcoded Starbucks mock data for template visual testing.
 */

export const BRAND = {
  name: "Starbucks",
  primary: "#00704A",
  secondary: "#1E3932",
  accent: "#D4E9E2",
  gold: "#CBA258",
  warmWhite: "#F2F0EB",
  logo: "https://upload.wikimedia.org/wikipedia/en/thumb/d/d3/Starbucks_Corporation_Logo_2011.svg/1200px-Starbucks_Corporation_Logo_2011.svg.png",
} as const;

export const KPIS = [
  { label: "Total Revenue", value: "$2.4M", delta: "+12.3%", icon: "dollar-sign" },
  { label: "Avg Order Value", value: "$6.85", delta: "+3.1%", icon: "shopping-cart" },
  { label: "Active Stores", value: "847", delta: "+24", icon: "store" },
  { label: "Top Drink", value: "Caramel Macchiato", delta: "\u21912 spots", icon: "coffee" },
] as const;

export const DRINK_CATEGORIES = ["Espresso", "Frappuccino", "Tea", "ColdBrew", "Refreshers"] as const;

export const CHART_DATA = [
  { month: "Oct", Espresso: 180000, Frappuccino: 120000, Tea: 65000, ColdBrew: 95000, Refreshers: 72000 },
  { month: "Nov", Espresso: 195000, Frappuccino: 98000, Tea: 78000, ColdBrew: 88000, Refreshers: 65000 },
  { month: "Dec", Espresso: 220000, Frappuccino: 85000, Tea: 92000, ColdBrew: 76000, Refreshers: 58000 },
  { month: "Jan", Espresso: 210000, Frappuccino: 75000, Tea: 88000, ColdBrew: 82000, Refreshers: 62000 },
  { month: "Feb", Espresso: 225000, Frappuccino: 105000, Tea: 82000, ColdBrew: 90000, Refreshers: 70000 },
  { month: "Mar", Espresso: 240000, Frappuccino: 130000, Tea: 75000, ColdBrew: 98000, Refreshers: 80000 },
];

export const CHART_COLORS = ["#00704A", "#1E3932", "#D4E9E2", "#87CEAB", "#4A7C6F"];

export const TABLE_DATA = [
  { store: "Pike Place Reserve", city: "Seattle", state: "WA", revenue: "$412,500", orders: 58200 },
  { store: "Times Square", city: "New York", state: "NY", revenue: "$389,200", orders: 54100 },
  { store: "Michigan Ave", city: "Chicago", state: "IL", revenue: "$345,800", orders: 48700 },
  { store: "Union Square", city: "San Francisco", state: "CA", revenue: "$328,100", orders: 45300 },
  { store: "Magnificent Mile", city: "Chicago", state: "IL", revenue: "$312,400", orders: 43900 },
  { store: "Hollywood Blvd", city: "Los Angeles", state: "CA", revenue: "$298,700", orders: 41200 },
  { store: "Dupont Circle", city: "Washington", state: "DC", revenue: "$287,300", orders: 39800 },
  { store: "Newbury Street", city: "Boston", state: "MA", revenue: "$276,900", orders: 38100 },
  { store: "Pearl District", city: "Portland", state: "OR", revenue: "$265,400", orders: 36500 },
  { store: "South Congress", city: "Austin", state: "TX", revenue: "$254,100", orders: 35200 },
];

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  sql?: string;
  hasChart?: boolean;
  hasTable?: boolean;
  timestamp: string;
}

export const CHAT_MESSAGES: ChatMessage[] = [
  {
    role: "user",
    content: "What are the top 5 stores by revenue this quarter?",
    timestamp: "2:34 PM",
  },
  {
    role: "assistant",
    content:
      "Here are the top 5 stores by revenue for Q1 2024. Pike Place Reserve leads with $412,500, followed by Times Square at $389,200.",
    sql: "SELECT store_name, city, state, SUM(revenue) as total_revenue\nFROM starbucks.sales.transactions\nWHERE quarter = '2024-Q1'\nGROUP BY store_name, city, state\nORDER BY total_revenue DESC\nLIMIT 5",
    hasTable: true,
    timestamp: "2:34 PM",
  },
  {
    role: "user",
    content: "Show me monthly revenue by drink category",
    timestamp: "2:36 PM",
  },
  {
    role: "assistant",
    content:
      "Monthly revenue breakdown by drink category shows Espresso consistently leading, with Frappuccino sales picking up in warmer months.",
    sql: "SELECT DATE_TRUNC('month', order_date) as month,\n       drink_category,\n       SUM(revenue) as total_revenue\nFROM starbucks.sales.transactions\nGROUP BY month, drink_category\nORDER BY month, total_revenue DESC",
    hasChart: true,
    timestamp: "2:36 PM",
  },
  {
    role: "user",
    content: "Which drink category is growing fastest?",
    timestamp: "2:38 PM",
  },
  {
    role: "assistant",
    content:
      "Refreshers is the fastest growing category at +24.1% quarter-over-quarter, driven by seasonal demand and new flavor launches.",
    sql: "SELECT drink_category,\n       SUM(CASE WHEN quarter='2024-Q1' THEN revenue END) as q1,\n       SUM(CASE WHEN quarter='2023-Q4' THEN revenue END) as q4,\n       ROUND((q1 - q4) / q4 * 100, 1) as growth_pct\nFROM starbucks.sales.transactions\nGROUP BY drink_category\nORDER BY growth_pct DESC",
    hasChart: true,
    timestamp: "2:38 PM",
  },
];

export const SUGGESTED_QUERIES = [
  { category: "Revenue", query: "Revenue by region last quarter", icon: "dollar-sign" },
  { category: "Stores", query: "Top performing new stores", icon: "store" },
  { category: "Products", query: "Best selling drinks this month", icon: "coffee" },
  { category: "Trends", query: "Year-over-year growth trends", icon: "trending-up" },
] as const;
