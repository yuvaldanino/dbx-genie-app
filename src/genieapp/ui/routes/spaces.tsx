/**
 * Spaces page — browse previously created Genie Spaces or create a new one.
 */

import { useState } from "react";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useSpaces, useDeleteSpace, useAdminCheck, type SpaceOut } from "@/lib/api";
import { useAuth } from "@/components/apx/AuthProvider";
import { useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Sparkles,
  Plus,
  ArrowLeft,
  Building2,
  MessageSquare,
  Shield,
  Trash2,
  User,
} from "lucide-react";

export const Route = createFileRoute("/spaces")({
  component: SpacesPage,
});

function SpaceCard({
  space,
  navigate,
  onDelete,
}: {
  space: SpaceOut;
  navigate: ReturnType<typeof useNavigate>;
  onDelete?: (spaceId: string) => void;
}) {
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleteInput, setDeleteInput] = useState("");

  const canDelete = deleteInput === space.company_name;

  return (
    <>
      <Card
        className="bg-card/80 backdrop-blur-sm cursor-pointer hover:border-primary/50 transition-colors relative group"
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
        {onDelete && (
          <button
            className="absolute top-3 right-3 p-1.5 rounded-md opacity-0 group-hover:opacity-100 transition-opacity bg-destructive/10 hover:bg-destructive/20 text-destructive"
            title="Delete space"
            onClick={(e) => {
              e.stopPropagation();
              setDeleteOpen(true);
              setDeleteInput("");
            }}
          >
            <Trash2 className="h-4 w-4" />
          </button>
        )}
      </Card>

      {/* Delete confirmation modal */}
      {deleteOpen && (
        <>
          <div className="fixed inset-0 bg-black/40 z-50" onClick={() => setDeleteOpen(false)} />
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <Card className="w-full max-w-md bg-card shadow-2xl border">
              <CardContent className="p-5 space-y-4">
                <div className="flex items-center gap-2 text-destructive">
                  <Trash2 className="h-5 w-5" />
                  <h3 className="font-semibold">Delete Space</h3>
                </div>
                <p className="text-sm text-muted-foreground">
                  This action cannot be undone. To confirm, type <strong className="text-foreground">{space.company_name}</strong> below:
                </p>
                <Input
                  value={deleteInput}
                  onChange={(e) => setDeleteInput(e.target.value)}
                  placeholder={space.company_name}
                  autoFocus
                />
                <div className="flex gap-2 justify-end">
                  <Button variant="outline" size="sm" onClick={() => setDeleteOpen(false)}>
                    Cancel
                  </Button>
                  <Button
                    variant="destructive"
                    size="sm"
                    disabled={!canDelete}
                    onClick={() => {
                      onDelete?.(space.space_id);
                      setDeleteOpen(false);
                    }}
                  >
                    Delete
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        </>
      )}
    </>
  );
}

function SpacesPage() {
  const navigate = useNavigate();
  const { data: spaces, isLoading } = useSpaces();
  const queryClient = useQueryClient();
  const deleteSpace = useDeleteSpace();
  const { data: adminCheck } = useAdminCheck();
  const { user } = useAuth();

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
        {/* Logged in as */}
        {user?.email && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground mb-6">
            <User className="h-3.5 w-3.5" />
            <span>Logged in as <span className="text-foreground font-medium">{user.email}</span></span>
          </div>
        )}

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
            {adminCheck?.is_admin && (
              <Button
                variant="outline"
                className="gap-2"
                onClick={() => navigate({ to: "/admin" })}
              >
                <Shield className="h-4 w-4" />
                Admin
              </Button>
            )}
            <Button
              className="gap-2"
              onClick={() => navigate({ to: "/" })}
            >
              <Plus className="h-4 w-4" />
              Create New
            </Button>
          </div>
        </div>

        {/* Spaces grid */}
        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[0, 1, 2, 3, 4, 5].map((i) => (
              <Card key={`sk-${i}`} className="bg-card/80">
                <CardContent className="py-6 space-y-3">
                  <div className="flex items-center gap-3">
                    <Skeleton className="h-10 w-10 rounded-md" />
                    <Skeleton className="h-5 w-2/3" />
                  </div>
                  <Skeleton className="h-3.5 w-full" />
                  <Skeleton className="h-3.5 w-4/5" />
                </CardContent>
              </Card>
            ))}
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
          <>
            {/* My Spaces — user-owned (BYOG + pipeline-created) */}
            {spaces.filter((s) => s.space_type !== "shared").length > 0 && (
              <div className="mb-8">
                <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
                  <Sparkles className="h-4 w-4 text-primary" />
                  My Spaces
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {spaces
                    .filter((s) => s.space_type !== "shared")
                    .map((space) => (
                      <SpaceCard
                        key={space.space_id}
                        space={space}
                        navigate={navigate}
                        onDelete={(id) => {
                          // Optimistically remove from cache immediately
                          queryClient.setQueryData<SpaceOut[]>(["spaces"], (old) =>
                            old ? old.filter((s) => s.space_id !== id) : [],
                          );
                          deleteSpace.mutate(id, {
                            onSuccess: () => queryClient.invalidateQueries({ queryKey: ["spaces"] }),
                            onError: () => queryClient.invalidateQueries({ queryKey: ["spaces"] }),
                          });
                        }}
                      />
                    ))}
                </div>
              </div>
            )}

            {/* Shared Spaces — premade demos from sessions table */}
            {spaces.filter((s) => s.space_type === "shared").length > 0 && (
              <div>
                <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
                  <Building2 className="h-4 w-4 text-muted-foreground" />
                  Shared Spaces
                </h2>
                <p className="text-sm text-muted-foreground mb-3">
                  Premade demo spaces available to everyone.
                </p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {spaces
                    .filter((s) => s.space_type === "shared")
                    .map((space) => (
                      <SpaceCard key={space.space_id} space={space} navigate={navigate} />
                    ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
