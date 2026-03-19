/**
 * Spaces page — browse previously created Genie Spaces, create new, or connect existing (BYOG).
 */

import { useState } from "react";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useSpaces, useCreateByogSpace } from "@/lib/api";
import { useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Sparkles,
  Plus,
  ArrowLeft,
  Building2,
  MessageSquare,
  Link2,
  X,
  Loader2,
  MessageCircle,
  LayoutDashboard,
  Command,
  PanelLeftClose,
} from "lucide-react";

export const Route = createFileRoute("/spaces")({
  component: SpacesPage,
});

const TEMPLATE_OPTIONS = [
  { id: "simple", label: "Simple Chat", icon: MessageSquare },
  { id: "widget", label: "Floating Widget", icon: MessageCircle },
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { id: "command", label: "Command Palette", icon: Command },
  { id: "workspace", label: "Query Workspace", icon: PanelLeftClose },
] as const;

function SpacesPage() {
  const navigate = useNavigate();
  const { data: spaces, isLoading } = useSpaces();
  const queryClient = useQueryClient();
  const createByog = useCreateByogSpace();

  const [showByogForm, setShowByogForm] = useState(false);
  const [byogSpaceId, setByogSpaceId] = useState("");
  const [byogCompanyName, setByogCompanyName] = useState("");
  const [byogPrimary, setByogPrimary] = useState("#4F46E5");
  const [byogSecondary, setByogSecondary] = useState("#7C3AED");
  const [byogTemplate, setByogTemplate] = useState("simple");
  const [byogError, setByogError] = useState<string | null>(null);

  /** Submit BYOG form. */
  function handleByogSubmit() {
    if (!byogSpaceId.trim() || !byogCompanyName.trim()) return;
    setByogError(null);
    createByog.mutate(
      {
        space_id: byogSpaceId.trim(),
        company_name: byogCompanyName.trim(),
        primary_color: byogPrimary,
        secondary_color: byogSecondary,
        template_id: byogTemplate,
      },
      {
        onSuccess: (space) => {
          queryClient.invalidateQueries({ queryKey: ["spaces"] });
          setShowByogForm(false);
          navigate({ to: "/chat", search: { spaceId: space.space_id } });
        },
        onError: (err) => {
          setByogError(
            err instanceof Error ? err.message : "Failed to connect space. Check the Space ID and try again.",
          );
        },
      },
    );
  }

  return (
    <div
      className="min-h-screen w-screen relative overflow-auto"
      style={{
        background:
          "linear-gradient(135deg, hsl(from var(--primary) h s l / 0.08) 0%, hsl(from var(--accent) h s l / 0.06) 50%, hsl(from var(--primary) h s l / 0.03) 100%)",
      }}
    >
      {/* Background decorations */}
      <div className="absolute top-[-20%] right-[-10%] w-[600px] h-[600px] rounded-full opacity-20 blur-3xl bg-primary" />
      <div className="absolute bottom-[-20%] left-[-10%] w-[500px] h-[500px] rounded-full opacity-15 blur-3xl bg-accent" />

      <div className="relative z-10 max-w-4xl mx-auto px-6 py-12">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <Button
              variant="ghost"
              size="sm"
              className="gap-1 mb-2 -ml-2"
              onClick={() => navigate({ to: "/" })}
            >
              <ArrowLeft className="h-4 w-4" />
              Back
            </Button>
            <h1 className="text-3xl font-bold flex items-center gap-3">
              <Sparkles className="h-7 w-7 text-primary" />
              Genie Spaces
            </h1>
            <p className="text-muted-foreground mt-1">
              Select an existing space or create a new one.
            </p>
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              className="gap-2"
              onClick={() => setShowByogForm(!showByogForm)}
            >
              <Link2 className="h-4 w-4" />
              Connect Existing
            </Button>
            <Button
              className="gap-2"
              onClick={() => navigate({ to: "/" })}
            >
              <Plus className="h-4 w-4" />
              Create New
            </Button>
          </div>
        </div>

        {/* BYOG Form */}
        {showByogForm && (
          <Card className="bg-card/80 backdrop-blur-sm mb-6">
            <CardContent className="p-6 space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold">Connect Existing Genie Space</h2>
                <Button variant="ghost" size="icon" onClick={() => setShowByogForm(false)}>
                  <X className="h-4 w-4" />
                </Button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium mb-1 block">Genie Space ID *</label>
                  <Input
                    value={byogSpaceId}
                    onChange={(e) => setByogSpaceId(e.target.value)}
                    placeholder="01ef..."
                    disabled={createByog.isPending}
                  />
                </div>
                <div>
                  <label className="text-sm font-medium mb-1 block">Company Name *</label>
                  <Input
                    value={byogCompanyName}
                    onChange={(e) => setByogCompanyName(e.target.value)}
                    placeholder="Acme Corp"
                    disabled={createByog.isPending}
                  />
                </div>
                <div>
                  <label className="text-sm font-medium mb-1 block">Primary Color</label>
                  <div className="flex gap-2">
                    <input
                      type="color"
                      value={byogPrimary}
                      onChange={(e) => setByogPrimary(e.target.value)}
                      className="h-9 w-12 rounded border cursor-pointer"
                      disabled={createByog.isPending}
                    />
                    <Input
                      value={byogPrimary}
                      onChange={(e) => setByogPrimary(e.target.value)}
                      className="flex-1"
                      disabled={createByog.isPending}
                    />
                  </div>
                </div>
                <div>
                  <label className="text-sm font-medium mb-1 block">Secondary Color</label>
                  <div className="flex gap-2">
                    <input
                      type="color"
                      value={byogSecondary}
                      onChange={(e) => setByogSecondary(e.target.value)}
                      className="h-9 w-12 rounded border cursor-pointer"
                      disabled={createByog.isPending}
                    />
                    <Input
                      value={byogSecondary}
                      onChange={(e) => setByogSecondary(e.target.value)}
                      className="flex-1"
                      disabled={createByog.isPending}
                    />
                  </div>
                </div>
              </div>

              {/* Template selector */}
              <div>
                <label className="text-sm font-medium mb-2 block">Template</label>
                <div className="flex flex-wrap gap-2">
                  {TEMPLATE_OPTIONS.map((t) => {
                    const Icon = t.icon;
                    return (
                      <Button
                        key={t.id}
                        variant={byogTemplate === t.id ? "default" : "outline"}
                        size="sm"
                        className="gap-1.5"
                        onClick={() => setByogTemplate(t.id)}
                        disabled={createByog.isPending}
                      >
                        <Icon className="h-3.5 w-3.5" />
                        {t.label}
                      </Button>
                    );
                  })}
                </div>
              </div>

              {/* Error */}
              {byogError && (
                <div className="rounded-md bg-destructive/10 border border-destructive/30 px-3 py-2">
                  <span className="text-sm text-destructive">{byogError}</span>
                </div>
              )}

              <Button
                className="w-full gap-2"
                onClick={handleByogSubmit}
                disabled={!byogSpaceId.trim() || !byogCompanyName.trim() || createByog.isPending}
              >
                {createByog.isPending ? (
                  <><Loader2 className="h-4 w-4 animate-spin" /> Connecting...</>
                ) : (
                  <><Link2 className="h-4 w-4" /> Connect Space</>
                )}
              </Button>
            </CardContent>
          </Card>
        )}

        {/* Spaces grid */}
        {isLoading ? (
          <div className="text-center text-muted-foreground py-12">
            Loading spaces...
          </div>
        ) : !spaces || spaces.length === 0 ? (
          <Card className="bg-card/80 backdrop-blur-sm">
            <CardContent className="flex flex-col items-center justify-center py-16">
              <Building2 className="h-12 w-12 text-muted-foreground/50 mb-4" />
              <p className="text-muted-foreground mb-4">
                No Genie Spaces created yet.
              </p>
              <Button
                className="gap-2"
                onClick={() => navigate({ to: "/" })}
              >
                <Plus className="h-4 w-4" />
                Create Your First Space
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {spaces.map((space) => (
              <Card
                key={space.space_id}
                className="bg-card/80 backdrop-blur-sm cursor-pointer hover:border-primary/50 transition-colors"
                onClick={() => navigate({ to: "/chat", search: { spaceId: space.space_id } })}
              >
                <CardContent className="p-5">
                  <div className="flex items-start gap-4">
                    {space.logo_path ? (
                      <img
                        src={space.logo_path}
                        alt={space.company_name}
                        className="h-12 w-12 object-contain rounded"
                      />
                    ) : (
                      <div
                        className="h-12 w-12 rounded flex items-center justify-center text-white font-bold text-lg shrink-0"
                        style={{ backgroundColor: space.primary_color }}
                      >
                        {space.company_name.charAt(0)}
                      </div>
                    )}
                    <div className="flex-1 min-w-0">
                      <h3 className="font-semibold truncate">
                        {space.company_name}
                      </h3>
                      <p className="text-sm text-muted-foreground line-clamp-2 mt-1">
                        {space.description || "No description"}
                      </p>
                      <div className="flex items-center gap-1 mt-3 text-xs text-muted-foreground">
                        <MessageSquare className="h-3 w-3" />
                        <span>Open Chat</span>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
