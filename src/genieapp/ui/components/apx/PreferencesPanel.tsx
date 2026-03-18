/**
 * PreferencesPanel — user preferences (theme, default template).
 * Saves to DB via PATCH /api/users/me/preferences.
 */

import { useState } from "react";
import { useAuth } from "./AuthProvider";
import { useUpdateUserPreferences } from "@/lib/api";
import { useTheme } from "./theme-provider";
import { Button } from "@/components/ui/button";
import { useQueryClient } from "@tanstack/react-query";
import { Settings, X } from "lucide-react";

const TEMPLATES = [
  { id: "simple", label: "Simple Chat" },
  { id: "widget", label: "Floating Widget" },
  { id: "dashboard", label: "Dashboard + Chat" },
  { id: "command", label: "Command Palette" },
  { id: "workspace", label: "Query Workspace" },
];

interface PreferencesPanelProps {
  open: boolean;
  onClose: () => void;
}

export function PreferencesPanel({ open, onClose }: PreferencesPanelProps) {
  const { user } = useAuth();
  const { theme, setTheme } = useTheme();
  const updatePrefs = useUpdateUserPreferences();
  const queryClient = useQueryClient();
  const [defaultTemplate, setDefaultTemplate] = useState(
    user?.default_template || "simple",
  );

  if (!open) return null;

  const handleSaveTemplate = (templateId: string) => {
    setDefaultTemplate(templateId);
    updatePrefs.mutate(
      { default_template: templateId },
      {
        onSuccess: () => {
          queryClient.invalidateQueries({ queryKey: ["currentUser"] });
        },
      },
    );
  };

  const handleSaveTheme = (newTheme: string) => {
    setTheme(newTheme as "light" | "dark" | "system");
    updatePrefs.mutate(
      { preferences: { theme: newTheme } },
      {
        onSuccess: () => {
          queryClient.invalidateQueries({ queryKey: ["currentUser"] });
        },
      },
    );
  };

  return (
    <div className="absolute bottom-12 left-2 right-2 bg-popover border rounded-lg shadow-lg p-4 z-50 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Settings className="h-4 w-4" />
          <span className="text-sm font-medium">Preferences</span>
        </div>
        <Button variant="ghost" size="icon" className="h-6 w-6" onClick={onClose}>
          <X className="h-3 w-3" />
        </Button>
      </div>

      {/* Default template */}
      <div className="space-y-1.5">
        <label className="text-xs text-muted-foreground">Default Template</label>
        <div className="flex flex-wrap gap-1">
          {TEMPLATES.map((t) => (
            <button
              key={t.id}
              onClick={() => handleSaveTemplate(t.id)}
              className={`px-2 py-1 rounded text-[11px] border transition-colors ${
                defaultTemplate === t.id
                  ? "bg-primary text-primary-foreground border-primary"
                  : "bg-background hover:bg-accent border-border"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* Theme */}
      <div className="space-y-1.5">
        <label className="text-xs text-muted-foreground">Theme</label>
        <div className="flex gap-1">
          {["light", "dark", "system"].map((t) => (
            <button
              key={t}
              onClick={() => handleSaveTheme(t)}
              className={`px-2 py-1 rounded text-[11px] border capitalize transition-colors ${
                theme === t
                  ? "bg-primary text-primary-foreground border-primary"
                  : "bg-background hover:bg-accent border-border"
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {user && user.user_id !== "anonymous" && (
        <div className="text-[10px] text-muted-foreground pt-1 border-t">
          Signed in as {user.email || user.username || user.user_id}
        </div>
      )}
    </div>
  );
}
