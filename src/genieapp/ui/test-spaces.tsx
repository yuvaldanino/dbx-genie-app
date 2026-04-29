/**
 * Sandbox copy of the Spaces page with:
 * 1. "Connect Existing" button removed
 * 2. "Logged in as [email]" shown at top
 *
 * NO API calls — uses mock data.
 */

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
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

// Mock data
const mockSpaces = [
  {
    space_id: "sp-1",
    company_name: "Nike",
    description: "Global athletic footwear and apparel company tracking sales, inventory, and regional performance.",
    logo_path: "",
    primary_color: "#F97316",
    space_type: "owned",
  },
  {
    space_id: "sp-2",
    company_name: "Forkable",
    description: "Corporate meal ordering platform with 2,000+ restaurant partners across 15 cities.",
    logo_path: "",
    primary_color: "#10B981",
    space_type: "owned",
  },
  {
    space_id: "sp-3",
    company_name: "TechStart Demo",
    description: "Sample fintech startup with customer, transaction, and product data.",
    logo_path: "",
    primary_color: "#6366F1",
    space_type: "shared",
  },
  {
    space_id: "sp-4",
    company_name: "RetailCo Demo",
    description: "National retail chain with store locations, inventory, and sales analytics.",
    logo_path: "",
    primary_color: "#EC4899",
    space_type: "shared",
  },
];

function MockSpaceCard({ space }: { space: (typeof mockSpaces)[0] }) {
  return (
    <Card className="bg-card/80 backdrop-blur-sm cursor-pointer hover:border-primary/50 transition-colors relative group">
      <CardContent className="p-5">
        <div className="flex items-start gap-4">
          <div
            className="h-12 w-12 rounded flex items-center justify-center text-white font-bold text-lg shrink-0"
            style={{ backgroundColor: space.primary_color }}
          >
            {space.company_name.charAt(0)}
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold truncate">{space.company_name}</h3>
            <p className="text-sm text-muted-foreground line-clamp-2 mt-1">
              {space.description}
            </p>
            <div className="flex items-center gap-1 mt-3 text-xs text-muted-foreground">
              <MessageSquare className="h-3 w-3" />
              <span>Open Chat</span>
            </div>
          </div>
        </div>
        {space.space_type !== "shared" && (
          <button
            className="absolute top-3 right-3 p-1.5 rounded-md opacity-0 group-hover:opacity-100 transition-opacity bg-destructive/10 hover:bg-destructive/20 text-destructive"
            title="Delete space"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        )}
      </CardContent>
    </Card>
  );
}

export function TestSpacesPage() {
  const mockEmail = "yuval.danino@databricks.com";
  const mySpaces = mockSpaces.filter((s) => s.space_type !== "shared");
  const sharedSpaces = mockSpaces.filter((s) => s.space_type === "shared");

  return (
    <div
      className="min-h-screen w-full relative overflow-auto"
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
        <div className="flex items-center gap-2 text-xs text-muted-foreground mb-6">
          <User className="h-3.5 w-3.5" />
          <span>Logged in as <span className="text-foreground font-medium">{mockEmail}</span></span>
        </div>

        {/* Header — NO "Connect Existing" button */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <Button variant="ghost" size="sm" className="gap-1 mb-2 -ml-2">
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
            <Button variant="outline" className="gap-2">
              <Shield className="h-4 w-4" />
              Admin
            </Button>
            {/* "Connect Existing" button REMOVED */}
            <Button className="gap-2">
              <Plus className="h-4 w-4" />
              Create New
            </Button>
          </div>
        </div>

        {/* My Spaces */}
        {mySpaces.length > 0 && (
          <div className="mb-8">
            <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-primary" />
              My Spaces
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {mySpaces.map((space) => (
                <MockSpaceCard key={space.space_id} space={space} />
              ))}
            </div>
          </div>
        )}

        {/* Shared Spaces */}
        {sharedSpaces.length > 0 && (
          <div>
            <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
              <Building2 className="h-4 w-4 text-muted-foreground" />
              Shared Spaces
            </h2>
            <p className="text-sm text-muted-foreground mb-3">
              Premade demo spaces available to everyone.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {sharedSpaces.map((space) => (
                <MockSpaceCard key={space.space_id} space={space} />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
