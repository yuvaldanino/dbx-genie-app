/**
 * Admin dashboard — usage metrics, user activity, space management.
 * Only accessible to admin users.
 */

import { useState } from "react";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import {
  useAdminCheck,
  useAdminStats,
  useAdminUsageTrend,
  useAdminUsers,
  useAdminSpaces,
  useToggleShared,
} from "@/lib/api";
import { useQueryClient } from "@tanstack/react-query";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Users,
  Layers,
  MessageSquare,
  TrendingUp,
  Shield,
  Globe,
  Lock,
  Activity,
  ArrowLeft,
  ArrowUpDown,
} from "lucide-react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

export const Route = createFileRoute("/admin")({
  component: AdminPage,
});

function AdminPage() {
  const navigate = useNavigate();
  const { data: adminCheck, isLoading: checkLoading } = useAdminCheck();
  const { data: stats } = useAdminStats();
  const { data: trend } = useAdminUsageTrend();
  const { data: users } = useAdminUsers();
  const { data: spaces } = useAdminSpaces();
  const toggleShared = useToggleShared();
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<"users" | "spaces">("users");
  const [userSort, setUserSort] = useState<{ key: string; dir: "asc" | "desc" }>({ key: "last_active", dir: "desc" });
  const [spaceSort, setSpaceSort] = useState<{ key: string; dir: "asc" | "desc" }>({ key: "created_at", dir: "desc" });

  if (checkLoading) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground">
        Loading...
      </div>
    );
  }

  if (!adminCheck?.is_admin) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4">
        <Shield className="h-12 w-12 text-muted-foreground/50" />
        <p className="text-muted-foreground">Admin access required.</p>
        <Button variant="outline" onClick={() => navigate({ to: "/" })}>
          Go Home
        </Button>
      </div>
    );
  }

  function handleToggleShared(spaceId: string, currentlyShared: boolean) {
    toggleShared.mutate(
      { spaceId, shared: !currentlyShared },
      {
        onSuccess: () => {
          queryClient.invalidateQueries({ queryKey: ["adminSpaces"] });
          queryClient.invalidateQueries({ queryKey: ["spaces"] });
        },
      },
    );
  }

  function sortData<T extends Record<string, unknown>>(data: T[] | undefined, sort: { key: string; dir: "asc" | "desc" }): T[] {
    if (!data) return [];
    return [...data].sort((a, b) => {
      let av = a[sort.key], bv = b[sort.key];
      if (av == null && bv == null) return 0;
      if (av == null) return 1;
      if (bv == null) return -1;
      // Coerce numeric strings to numbers for proper sorting
      const an = Number(av), bn = Number(bv);
      const cmp = !isNaN(an) && !isNaN(bn)
        ? an - bn
        : String(av).localeCompare(String(bv));
      return sort.dir === "asc" ? cmp : -cmp;
    });
  }

  function toggleSort(current: { key: string; dir: "asc" | "desc" }, key: string): { key: string; dir: "asc" | "desc" } {
    if (current.key === key) return { key, dir: current.dir === "asc" ? "desc" : "asc" };
    return { key, dir: "desc" };
  }

  const sortedUsers = sortData(users, userSort);
  const sortedSpaces = sortData(spaces, spaceSort);

  const kpis = [
    { label: "Total Users", value: stats?.total_users ?? 0, icon: Users },
    { label: "Total Spaces", value: stats?.total_spaces ?? 0, icon: Layers },
    { label: "Total Conversations", value: stats?.total_conversations ?? 0, icon: MessageSquare },
    { label: "Total Messages", value: stats?.total_messages ?? 0, icon: MessageSquare },
    { label: "Messages This Week", value: stats?.messages_this_week ?? 0, icon: TrendingUp },
    { label: "Active Users This Week", value: stats?.active_users_this_week ?? 0, icon: Activity },
  ];

  return (
    <div
      className="min-h-screen w-screen relative overflow-auto"
      style={{
        background:
          "linear-gradient(135deg, hsl(from var(--primary) h s l / 0.08) 0%, hsl(from var(--accent) h s l / 0.06) 50%, hsl(from var(--primary) h s l / 0.03) 100%)",
      }}
    >
      <div className="absolute top-[-20%] right-[-10%] w-[600px] h-[600px] rounded-full opacity-20 blur-3xl bg-primary" />
      <div className="absolute bottom-[-20%] left-[-10%] w-[500px] h-[500px] rounded-full opacity-15 blur-3xl bg-accent" />

    <div className="relative z-10 max-w-5xl mx-auto px-6 py-12 space-y-6">
      {/* Header */}
      <div>
        <Button
          variant="ghost"
          size="sm"
          className="gap-1 mb-2 -ml-2"
          onClick={() => navigate({ to: "/spaces" })}
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Spaces
        </Button>
        <div className="flex items-center gap-3">
          <Shield className="h-7 w-7 text-primary" />
          <h1 className="text-3xl font-bold">Admin Dashboard</h1>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        {kpis.map((kpi) => {
          const Icon = kpi.icon;
          return (
            <Card key={kpi.label}>
              <CardContent className="p-4">
                <div className="flex items-center gap-2 text-muted-foreground mb-1">
                  <Icon className="h-4 w-4" />
                  <span className="text-xs">{kpi.label}</span>
                </div>
                <p className="text-2xl font-bold">{kpi.value.toLocaleString()}</p>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Usage Trend Chart */}
      <Card>
        <CardContent className="p-4">
          <h2 className="text-sm font-semibold mb-3">Messages Per Day (Last 30 Days)</h2>
          {trend && trend.length > 0 ? (() => {
            const chartData = trend.map((d) => ({ ...d, count: Number(d.count) || 0 }));
            return (
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 10 }}>
                <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
                <XAxis
                  dataKey="day"
                  tick={{ fontSize: 11 }}
                  tickFormatter={(v: string) => v.slice(5)}
                />
                <YAxis tick={{ fontSize: 11 }} domain={[0, "dataMax"]} allowDecimals={false} />
                <Tooltip />
                <Line
                  type="monotone"
                  dataKey="count"
                  stroke="var(--chart-1)"
                  strokeWidth={2}
                  dot={{ r: 2 }}
                />
              </LineChart>
            </ResponsiveContainer>
            );
          })() : (
            <p className="text-sm text-muted-foreground text-center py-8">No usage data yet</p>
          )}
        </CardContent>
      </Card>

      {/* Tabs */}
      <div className="flex gap-2 border-b pb-2">
        <Button
          variant={tab === "users" ? "default" : "ghost"}
          size="sm"
          onClick={() => setTab("users")}
          className="gap-1.5"
        >
          <Users className="h-3.5 w-3.5" />
          Users ({users?.length ?? 0})
        </Button>
        <Button
          variant={tab === "spaces" ? "default" : "ghost"}
          size="sm"
          onClick={() => setTab("spaces")}
          className="gap-1.5"
        >
          <Layers className="h-3.5 w-3.5" />
          Spaces ({spaces?.length ?? 0})
        </Button>
      </div>

      {/* Users Table */}
      {tab === "users" && (
        <Card>
          <CardContent className="p-0">
            <div className="overflow-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-muted/50">
                    <th className="px-4 py-3 text-left font-medium text-muted-foreground">User</th>
                    <th className="px-4 py-3 text-left font-medium text-muted-foreground cursor-pointer hover:text-foreground" onClick={() => setUserSort(toggleSort(userSort, "spaces_created"))}>
                      <span className="inline-flex items-center gap-1">Spaces <ArrowUpDown className="h-3 w-3" /></span>
                    </th>
                    <th className="px-4 py-3 text-left font-medium text-muted-foreground cursor-pointer hover:text-foreground" onClick={() => setUserSort(toggleSort(userSort, "last_active"))}>
                      <span className="inline-flex items-center gap-1">Last Active <ArrowUpDown className="h-3 w-3" /></span>
                    </th>
                    <th className="px-4 py-3 text-left font-medium text-muted-foreground cursor-pointer hover:text-foreground" onClick={() => setUserSort(toggleSort(userSort, "joined"))}>
                      <span className="inline-flex items-center gap-1">Joined <ArrowUpDown className="h-3 w-3" /></span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {sortedUsers.map((u) => (
                    <tr key={u.user_id} className="border-b hover:bg-muted/30">
                      <td className="px-4 py-3">
                        <div>
                          <p className="font-medium">{u.email || u.username || u.user_id}</p>
                          {u.email && u.username && (
                            <p className="text-xs text-muted-foreground">{u.username}</p>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3">{u.spaces_created}</td>
                      <td className="px-4 py-3 text-muted-foreground">
                        {u.last_active ? new Date(u.last_active).toLocaleDateString() : "Never"}
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">
                        {u.joined ? new Date(u.joined).toLocaleDateString() : "—"}
                      </td>
                    </tr>
                  ))}
                  {sortedUsers.length === 0 && (
                    <tr>
                      <td colSpan={4} className="px-4 py-8 text-center text-muted-foreground">
                        No users found
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Spaces Table */}
      {tab === "spaces" && (
        <Card>
          <CardContent className="p-0">
            <div className="overflow-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-muted/50">
                    <th className="px-4 py-3 text-left font-medium text-muted-foreground cursor-pointer hover:text-foreground" onClick={() => setSpaceSort(toggleSort(spaceSort, "company_name"))}>
                      <span className="inline-flex items-center gap-1">Space <ArrowUpDown className="h-3 w-3" /></span>
                    </th>
                    <th className="px-4 py-3 text-left font-medium text-muted-foreground">Owner</th>
                    <th className="px-4 py-3 text-left font-medium text-muted-foreground">Type</th>
                    <th className="px-4 py-3 text-left font-medium text-muted-foreground cursor-pointer hover:text-foreground" onClick={() => setSpaceSort(toggleSort(spaceSort, "message_count"))}>
                      <span className="inline-flex items-center gap-1">Messages <ArrowUpDown className="h-3 w-3" /></span>
                    </th>
                    <th className="px-4 py-3 text-left font-medium text-muted-foreground cursor-pointer hover:text-foreground" onClick={() => setSpaceSort(toggleSort(spaceSort, "created_at"))}>
                      <span className="inline-flex items-center gap-1">Created <ArrowUpDown className="h-3 w-3" /></span>
                    </th>
                    <th className="px-4 py-3 text-left font-medium text-muted-foreground">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {sortedSpaces.map((sp) => {
                    const isShared = sp.space_type === "shared";
                    return (
                      <tr key={sp.space_id} className="border-b hover:bg-muted/30">
                        <td className="px-4 py-3 font-medium">{sp.company_name}</td>
                        <td className="px-4 py-3 text-muted-foreground text-xs">
                          {sp.owner_email}
                        </td>
                        <td className="px-4 py-3">
                          <span
                            className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full ${
                              isShared
                                ? "bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300"
                                : "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300"
                            }`}
                          >
                            {isShared ? <Globe className="h-3 w-3" /> : <Lock className="h-3 w-3" />}
                            {sp.space_type}
                          </span>
                        </td>
                        <td className="px-4 py-3">{sp.message_count}</td>
                        <td className="px-4 py-3 text-muted-foreground">
                          {sp.created_at ? new Date(sp.created_at).toLocaleDateString() : "—"}
                        </td>
                        <td className="px-4 py-3">
                          <Button
                            variant="outline"
                            size="sm"
                            className="h-7 text-xs gap-1"
                            onClick={() => handleToggleShared(sp.space_id, isShared)}
                            disabled={toggleShared.isPending}
                          >
                            {isShared ? (
                              <><Lock className="h-3 w-3" /> Make Private</>
                            ) : (
                              <><Globe className="h-3 w-3" /> Make Shared</>
                            )}
                          </Button>
                        </td>
                      </tr>
                    );
                  })}
                  {sortedSpaces.length === 0 && (
                    <tr>
                      <td colSpan={6} className="px-4 py-8 text-center text-muted-foreground">
                        No spaces found
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
    </div>
  );
}
