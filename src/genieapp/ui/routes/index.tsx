/**
 * Landing page — create a new Genie Space by providing company name and description.
 * Supports logo via URL or file upload to UC Volumes.
 */

import { useState, useCallback, useRef } from "react";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { createSpace, getJobStatus, uploadImage, registerPipelineSpace } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import {
  Sparkles,
  ArrowRight,
  Loader2,
  History,
  AlertTriangle,
  Upload,
  Link2,
  X,
} from "lucide-react";

export const Route = createFileRoute("/")({
  component: LandingPage,
});

const PROGRESS_MESSAGES: Record<string, string> = {
  PENDING: "Queuing pipeline...",
  RUNNING: "Creating your Genie Space...",
  COMPLETED: "Done! Redirecting...",
  FAILED: "Pipeline failed.",
};

function LandingPage() {
  const navigate = useNavigate();

  const [companyName, setCompanyName] = useState("");
  const [description, setDescription] = useState("");
  const [logoUrl, setLogoUrl] = useState("");
  const [logoMode, setLogoMode] = useState<"url" | "upload">("url");
  const [logoFile, setLogoFile] = useState<File | null>(null);
  const [logoPreview, setLogoPreview] = useState<string | null>(null);
  const [uploadedPath, setUploadedPath] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [progress, setProgress] = useState("");
  const [error, setError] = useState<string | null>(null);

  /** Handle file selection and upload. */
  const handleFileSelect = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setLogoFile(file);
    setLogoPreview(URL.createObjectURL(file));
    setIsUploading(true);
    setError(null);

    try {
      const result = await uploadImage(file);
      setUploadedPath(result.volume_path);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to upload image");
      setLogoFile(null);
      setLogoPreview(null);
    } finally {
      setIsUploading(false);
    }
  }, []);

  /** Clear uploaded file. */
  const clearUpload = () => {
    setLogoFile(null);
    setLogoPreview(null);
    setUploadedPath(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  /** Resolve the logo value to pass to createSpace. */
  const resolvedLogoUrl = logoMode === "upload" && uploadedPath
    ? uploadedPath
    : logoUrl.trim() || undefined;

  const handleCreate = useCallback(async () => {
    if (!companyName.trim() || !description.trim() || isCreating) return;
    setIsCreating(true);
    setError(null);
    setProgress("Starting pipeline...");

    try {
      const { run_id } = await createSpace(companyName.trim(), description.trim(), resolvedLogoUrl);

      let attempts = 0;
      const maxAttempts = 200;

      while (attempts < maxAttempts) {
        await new Promise((r) => setTimeout(r, 3000));
        const status = await getJobStatus(run_id);
        setProgress(
          PROGRESS_MESSAGES[status.status] || `Status: ${status.status}`,
        );

        if (status.status === "COMPLETED") {
          if (status.space_id) {
            // Register pipeline space (copies session → spaces table)
            try {
              await registerPipelineSpace(status.space_id);
            } catch {
              // Non-critical — space may still work via sessions fallback
            }
            navigate({ to: "/chat", search: { spaceId: status.space_id } });
          } else {
            navigate({ to: "/spaces" });
          }
          return;
        }

        if (status.status === "FAILED") {
          setError(status.error || "Pipeline failed. Check the job logs in Databricks.");
          setIsCreating(false);
          return;
        }

        attempts++;
      }

      setError("Pipeline timed out. Check the job in Databricks.");
      setIsCreating(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to start pipeline");
      setIsCreating(false);
    }
  }, [companyName, description, resolvedLogoUrl, isCreating, navigate]);

  const canSubmit = companyName.trim().length > 0 && description.trim().length > 0 && !isCreating;

  return (
    <div
      className="h-screen w-screen flex flex-col items-center justify-center relative overflow-hidden"
      style={{
        background:
          "linear-gradient(135deg, hsl(from var(--primary) h s l / 0.08) 0%, hsl(from var(--accent) h s l / 0.06) 50%, hsl(from var(--primary) h s l / 0.03) 100%)",
      }}
    >
      {/* Background decorations */}
      <div className="absolute top-[-20%] right-[-10%] w-[600px] h-[600px] rounded-full opacity-20 blur-3xl bg-primary" />
      <div className="absolute bottom-[-20%] left-[-10%] w-[500px] h-[500px] rounded-full opacity-15 blur-3xl bg-accent" />

      {/* Content */}
      <div className="relative z-10 flex flex-col items-center text-center max-w-2xl w-full px-6">
        {/* Title */}
        <div className="flex items-center gap-3 mb-2">
          <Sparkles className="h-8 w-8 text-primary" />
          <h1 className="text-4xl md:text-5xl font-bold">GenieApp</h1>
        </div>
        <p className="text-muted-foreground mb-8">
          Create a custom AI-powered data space for any company in minutes.
        </p>

        <Card className="w-full max-w-lg p-6 space-y-5 bg-card/80 backdrop-blur-sm">
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
            />
          </div>

          {/* Logo — URL or Upload toggle */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium">
                Logo <span className="text-muted-foreground font-normal">(optional)</span>
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
              />
            ) : (
              <div className="space-y-2">
                {logoPreview ? (
                  <div className="flex items-center gap-3 rounded-md border p-2">
                    <img src={logoPreview} alt="Preview" className="h-10 w-10 object-contain rounded" />
                    <div className="flex-1 min-w-0">
                      <p className="text-xs truncate">{logoFile?.name}</p>
                      {isUploading && (
                        <p className="text-xs text-muted-foreground flex items-center gap-1">
                          <Loader2 className="h-3 w-3 animate-spin" /> Uploading...
                        </p>
                      )}
                      {uploadedPath && (
                        <p className="text-xs text-green-600">Uploaded</p>
                      )}
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
                    className="w-full border-2 border-dashed rounded-md py-6 text-center text-sm text-muted-foreground hover:border-primary/50 hover:text-foreground transition-colors cursor-pointer"
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
                  onChange={handleFileSelect}
                />
              </div>
            )}
          </div>

          {/* Company description */}
          <div>
            <label className="text-sm font-medium mb-2 block text-left">
              Company Description
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe the company and the type of data they work with. For example: 'Coca-Cola is a global beverage company. They track sales across 200+ countries, manage distribution logistics, and monitor retailer relationships...'"
              className="w-full min-h-[120px] rounded-md border bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring resize-y"
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
            className="w-full gap-2"
            disabled={!canSubmit}
            onClick={handleCreate}
          >
            {isCreating ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                {progress || "Creating Genie Space..."}
              </>
            ) : (
              <>
                Create Genie Space
                <ArrowRight className="h-4 w-4" />
              </>
            )}
          </Button>
        </Card>

        {/* Previous sessions link */}
        <Button
          variant="ghost"
          className="mt-4 gap-2 text-muted-foreground"
          onClick={() => navigate({ to: "/spaces" })}
        >
          <History className="h-4 w-4" />
          View Previous Sessions
        </Button>
      </div>
    </div>
  );
}
