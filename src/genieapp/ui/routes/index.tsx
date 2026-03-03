/**
 * Landing page — full-screen hero with company branding.
 */

import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useAppConfig } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Sparkles, ArrowRight } from "lucide-react";

export const Route = createFileRoute("/")({
  component: LandingPage,
});

function LandingPage() {
  const navigate = useNavigate();
  const { data: config } = useAppConfig();

  const branding = config?.branding;
  const primaryColor = branding?.primary_color || "#1a73e8";
  const secondaryColor = branding?.secondary_color || "#ea4335";

  return (
    <div
      className="h-screen w-screen flex flex-col items-center justify-center relative overflow-hidden"
      style={{
        background: `linear-gradient(135deg, ${primaryColor}15 0%, ${secondaryColor}10 50%, ${primaryColor}05 100%)`,
      }}
    >
      {/* Background decorations */}
      <div
        className="absolute top-[-20%] right-[-10%] w-[600px] h-[600px] rounded-full opacity-20 blur-3xl"
        style={{ background: primaryColor }}
      />
      <div
        className="absolute bottom-[-20%] left-[-10%] w-[500px] h-[500px] rounded-full opacity-15 blur-3xl"
        style={{ background: secondaryColor }}
      />

      {/* Content */}
      <div className="relative z-10 flex flex-col items-center text-center max-w-2xl px-6">
        {/* Logo */}
        {branding?.logo_path && (
          <img
            src={branding.logo_path}
            alt={branding.company_name}
            className="h-20 w-auto mb-6 drop-shadow-lg"
          />
        )}

        {/* Company name */}
        <h1 className="text-5xl md:text-6xl lg:text-7xl font-bold mb-4 bg-gradient-to-r from-foreground to-foreground/70 bg-clip-text">
          {branding?.company_name || __APP_NAME__}
        </h1>

        {/* Description */}
        {branding?.description && (
          <p className="text-lg text-muted-foreground mb-8 max-w-lg">
            {branding.description}
          </p>
        )}

        {/* Genie Space info */}
        <div className="flex items-center gap-2 text-sm text-muted-foreground mb-8">
          <Sparkles className="h-4 w-4" />
          <span>Powered by {config?.display_name || "Databricks Genie"}</span>
        </div>

        {/* CTA */}
        <Button
          size="lg"
          className="gap-2 text-base px-8 py-6 rounded-full shadow-lg"
          style={{ backgroundColor: primaryColor }}
          onClick={() => navigate({ to: "/chat" })}
        >
          Start Exploring Your Data
          <ArrowRight className="h-5 w-5" />
        </Button>
      </div>
    </div>
  );
}
