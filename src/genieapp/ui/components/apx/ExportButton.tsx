/**
 * Export conversation (JSON/CSV) or chart (PNG via html2canvas).
 */

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Download } from "lucide-react";
import { exportConversation } from "@/lib/api";

interface ExportButtonProps {
  conversationId: string;
  variant?: "default" | "ghost" | "outline";
  size?: "default" | "sm" | "icon";
}

export function ExportButton({
  conversationId,
  variant = "ghost",
  size = "sm",
}: ExportButtonProps) {
  const [exporting, setExporting] = useState(false);

  async function handleExportCSV() {
    setExporting(true);
    try {
      const blob = await exportConversation(conversationId, "csv");
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `conversation_${conversationId}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } finally {
      setExporting(false);
    }
  }

  async function handleExportChart() {
    const { default: html2canvas } = await import("html2canvas");
    const chartEl = document.getElementById("chart-container");
    if (!chartEl) return;
    const canvas = await html2canvas(chartEl);
    const url = canvas.toDataURL("image/png");
    const a = document.createElement("a");
    a.href = url;
    a.download = "chart.png";
    a.click();
  }

  return (
    <div className="flex gap-1">
      <Button
        variant={variant}
        size={size}
        onClick={handleExportCSV}
        disabled={exporting}
        title="Export data as CSV"
      >
        <Download className="h-4 w-4" />
        <span className="sr-only">Export CSV</span>
      </Button>
    </div>
  );
}
