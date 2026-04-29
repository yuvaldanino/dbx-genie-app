/**
 * Sandbox copy of the Landing Page (index.tsx) with layout improvements.
 *
 * Changes vs original:
 * 1. Wider card: max-w-lg (512px) → max-w-3xl (768px)
 * 2. Two-column layout for Company Name + Logo row
 * 3. Taller textareas with more breathing room
 * 4. More spacious padding and gaps
 * 5. Overall more horizontal, less cramped feel
 *
 * NO API calls — submit button is visual only.
 */

import { useState, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import {
  Sparkles,
  ArrowRight,
  Loader2,
  Clock,
  History,
  AlertTriangle,
  Upload,
  Link2,
  X,
  HelpCircle,
} from "lucide-react";

export function TestLandingPage() {
  const [companyName, setCompanyName] = useState("");
  const [description, setDescription] = useState("");
  const [logoUrl, setLogoUrl] = useState("");
  const [logoMode, setLogoMode] = useState<"url" | "upload">("url");
  const [logoFile, setLogoFile] = useState<File | null>(null);
  const [logoPreview, setLogoPreview] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [mustAnswerQuestions, setMustAnswerQuestions] = useState("");
  const [isCreating] = useState(false);
  const [error] = useState<string | null>(null);

  const clearUpload = () => {
    setLogoFile(null);
    setLogoPreview(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const canSubmit =
    companyName.trim().length > 0 && description.trim().length > 0 && !isCreating;

  return (
    <div
      className="min-h-screen w-full flex flex-col items-center justify-center relative overflow-hidden py-12"
      style={{
        background:
          "linear-gradient(135deg, hsl(from var(--primary) h s l / 0.08) 0%, hsl(from var(--accent) h s l / 0.06) 50%, hsl(from var(--primary) h s l / 0.03) 100%)",
      }}
    >
      {/* Help button */}
      <Button
        variant="outline"
        size="default"
        className="absolute top-6 right-6 z-20 gap-2 text-sm px-4 py-2"
      >
        <HelpCircle className="h-5 w-5" />
        Help
      </Button>

      {/* Background decorations */}
      <div className="absolute top-[-20%] right-[-10%] w-[600px] h-[600px] rounded-full opacity-20 blur-3xl bg-primary" />
      <div className="absolute bottom-[-20%] left-[-10%] w-[500px] h-[500px] rounded-full opacity-15 blur-3xl bg-accent" />

      {/* Content */}
      <div className="relative z-10 flex flex-col items-center text-center w-full px-6 max-w-4xl">
        {/* Title */}
        <div className="flex items-center gap-3 mb-2">
          <Sparkles className="h-8 w-8 text-primary" />
          <h1 className="text-4xl md:text-5xl font-bold">Genie-rator</h1>
        </div>
        <p className="text-muted-foreground mb-8">
          Generate a branded Genie Space with custom data — ready to query in
          minutes.
        </p>

        {/* ===== WIDER CARD with better contrast ===== */}
        <Card className="w-full p-8 space-y-6 bg-card/90 backdrop-blur-sm shadow-lg border-border/80">
          {/* Row 1: Company Name + Logo side by side */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Company name */}
            <div>
              <label className="text-sm font-medium mb-2 block text-left">
                Company Name
              </label>
              <Input
                value={companyName}
                onChange={(e) => setCompanyName(e.target.value)}
                placeholder="e.g. NovaTech Logistics"
                disabled={isCreating}
                className="h-11"
              />
            </div>

            {/* Logo — URL or Upload toggle */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-sm font-medium">
                  Logo{" "}
                  <span className="text-muted-foreground font-normal">
                    (optional)
                  </span>
                </label>
                <div className="flex border rounded-md overflow-hidden">
                  <button
                    type="button"
                    className={`px-2.5 py-1 text-xs flex items-center gap-1 transition-colors ${
                      logoMode === "url"
                        ? "bg-primary text-primary-foreground"
                        : "bg-background text-muted-foreground hover:text-foreground"
                    }`}
                    onClick={() => setLogoMode("url")}
                    disabled={isCreating}
                  >
                    <Link2 className="h-3 w-3" />
                    URL
                  </button>
                  <button
                    type="button"
                    className={`px-2.5 py-1 text-xs flex items-center gap-1 transition-colors ${
                      logoMode === "upload"
                        ? "bg-primary text-primary-foreground"
                        : "bg-background text-muted-foreground hover:text-foreground"
                    }`}
                    onClick={() => setLogoMode("upload")}
                    disabled={isCreating}
                  >
                    <Upload className="h-3 w-3" />
                    Upload
                  </button>
                </div>
              </div>

              {logoMode === "url" ? (
                <Input
                  value={logoUrl}
                  onChange={(e) => setLogoUrl(e.target.value)}
                  placeholder="https://logo.clearbit.com/company.com"
                  disabled={isCreating}
                  className="h-11"
                />
              ) : (
                <div className="space-y-2">
                  {logoPreview ? (
                    <div className="flex items-center gap-3 rounded-md border p-2">
                      <img
                        src={logoPreview}
                        alt="Preview"
                        className="h-10 w-10 object-contain rounded"
                      />
                      <div className="flex-1 min-w-0">
                        <p className="text-xs truncate">{logoFile?.name}</p>
                      </div>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7 shrink-0"
                        onClick={clearUpload}
                        disabled={isCreating}
                      >
                        <X className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  ) : (
                    <button
                      type="button"
                      className="w-full border-2 border-dashed rounded-md py-4 text-center text-sm text-muted-foreground hover:border-primary/50 hover:text-foreground transition-colors cursor-pointer"
                      onClick={() => fileInputRef.current?.click()}
                      disabled={isCreating}
                    >
                      <Upload className="h-5 w-5 mx-auto mb-1" />
                      Click to upload PNG, JPG, or SVG
                    </button>
                  )}
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/png,image/jpeg,image/svg+xml"
                    className="hidden"
                    onChange={() => {}}
                  />
                </div>
              )}
            </div>
          </div>

          {/* Company description — full width, taller */}
          <div>
            <label className="text-sm font-medium mb-2 block text-left">
              Company Description
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe the company and the type of data they work with. For example: 'Coca-Cola is a global beverage company. They track sales across 200+ countries, manage distribution logistics, and monitor retailer relationships...'"
              className="w-full min-h-[150px] rounded-md border bg-background px-4 py-3 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring resize-y"
              disabled={isCreating}
            />
          </div>

          {/* Must-answer questions — full width, taller */}
          <div>
            <label className="text-sm font-medium mb-2 block text-left">
              Questions this space should answer{" "}
              <span className="text-muted-foreground font-normal">
                (optional)
              </span>
            </label>
            <textarea
              value={mustAnswerQuestions}
              onChange={(e) => setMustAnswerQuestions(e.target.value)}
              placeholder={
                "e.g.,\nWhat is the total revenue by region?\nWhich product has the highest sales?\nWhat is the monthly trend for new customers?"
              }
              className="w-full min-h-[110px] rounded-md border bg-background px-4 py-3 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring resize-y"
              disabled={isCreating}
            />
          </div>

          {/* Error message */}
          {error && (
            <div className="flex items-start gap-2 rounded-md bg-destructive/10 border border-destructive/30 px-3 py-2">
              <AlertTriangle className="h-4 w-4 text-destructive shrink-0 mt-0.5" />
              <span className="text-sm text-destructive">{error}</span>
            </div>
          )}

          {/* Submit */}
          <Button
            size="lg"
            className="w-full gap-2 h-12 text-base"
            disabled={!canSubmit}
          >
            {isCreating ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Creating Genie Space...
              </>
            ) : (
              <>
                Create Genie Space
                <ArrowRight className="h-4 w-4" />
              </>
            )}
          </Button>
          {isCreating && (
            <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground mt-3">
              <Clock className="h-4 w-4" />
              <span>
                This usually takes 4-5 minutes. Feel free to wait — your space
                will be ready shortly.
              </span>
            </div>
          )}
        </Card>

        {/* Previous sessions link */}
        <Button variant="ghost" className="mt-4 gap-2 text-muted-foreground">
          <History className="h-4 w-4" />
          View Previous Sessions
        </Button>
      </div>
    </div>
  );
}
