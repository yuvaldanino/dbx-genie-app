/**
 * Spaces page — browse previously created Genie Spaces or create a new one.
 */

import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useSpaces } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Sparkles,
  Plus,
  ArrowLeft,
  Building2,
  MessageSquare,
} from "lucide-react";

export const Route = createFileRoute("/spaces")({
  component: SpacesPage,
});

function SpacesPage() {
  const navigate = useNavigate();
  const { data: spaces, isLoading } = useSpaces();

  return (
    <div
      className="min-h-screen w-screen relative overflow-auto"
      style={{
        background:
          "linear-gradient(135deg, oklch(0.55 0.19 255 / 0.08) 0%, oklch(0.60 0.16 165 / 0.06) 50%, oklch(0.55 0.19 255 / 0.03) 100%)",
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
          <Button
            className="gap-2"
            onClick={() => navigate({ to: "/" })}
          >
            <Plus className="h-4 w-4" />
            Create New
          </Button>
        </div>

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
                    {/* Logo or placeholder */}
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
