/**
 * Help dialog — guide + feedback tabs.
 */

import { useState } from "react";
import { X, BookOpen, MessageSquarePlus, Send, CheckCircle2, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useSubmitFeedback } from "@/lib/api";

interface HelpDialogProps {
  open: boolean;
  onClose: () => void;
}

export function HelpDialog({ open, onClose }: HelpDialogProps) {
  const [tab, setTab] = useState<"guide" | "feedback">("guide");
  const [feedbackText, setFeedbackText] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const submitFeedback = useSubmitFeedback();

  if (!open) return null;

  function handleSubmitFeedback() {
    if (!feedbackText.trim()) return;
    submitFeedback.mutate(feedbackText.trim(), {
      onSuccess: () => {
        setSubmitted(true);
        setFeedbackText("");
        setTimeout(() => setSubmitted(false), 3000);
      },
    });
  }

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/40 z-50" onClick={onClose} />

      {/* Dialog */}
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <Card className="w-full max-w-lg bg-card shadow-2xl border overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between border-b px-5 py-4">
            <h2 className="text-lg font-semibold">Help & Feedback</h2>
            <Button variant="ghost" size="icon" onClick={onClose}>
              <X className="h-4 w-4" />
            </Button>
          </div>

          {/* Tabs */}
          <div className="flex border-b">
            <button
              className={`flex-1 px-4 py-2.5 text-sm font-medium flex items-center justify-center gap-2 transition-colors ${
                tab === "guide"
                  ? "border-b-2 border-primary text-primary"
                  : "text-muted-foreground hover:text-foreground"
              }`}
              onClick={() => setTab("guide")}
            >
              <BookOpen className="h-4 w-4" />
              How It Works
            </button>
            <button
              className={`flex-1 px-4 py-2.5 text-sm font-medium flex items-center justify-center gap-2 transition-colors ${
                tab === "feedback"
                  ? "border-b-2 border-primary text-primary"
                  : "text-muted-foreground hover:text-foreground"
              }`}
              onClick={() => setTab("feedback")}
            >
              <MessageSquarePlus className="h-4 w-4" />
              Feedback
            </button>
          </div>

          {/* Content */}
          <div className="p-5">
            {tab === "guide" ? (
              <div className="space-y-4">
                <p className="text-sm text-muted-foreground">
                  Create your own AI-powered analytics space in minutes. Here's how:
                </p>

                <div className="space-y-3">
                  {[
                    {
                      step: "1",
                      title: "Enter your company name",
                      desc: "This will be used to brand your analytics space.",
                    },
                    {
                      step: "2",
                      title: "Describe your data",
                      desc: "Tell us what kind of data you want to analyze (e.g., \"sales data for a coffee chain with stores, products, and transactions\").",
                    },
                    {
                      step: "3",
                      title: "Optionally add a logo",
                      desc: "Upload a company logo or paste a URL to personalize your space.",
                    },
                    {
                      step: "4",
                      title: "Wait ~5 minutes",
                      desc: "We generate realistic sample data, create database tables, build a Genie Space, and design a dashboard for you.",
                    },
                    {
                      step: "5",
                      title: "Query with natural language",
                      desc: "Ask questions about your data in plain English. View results as charts, tables, and KPIs.",
                    },
                  ].map((item) => (
                    <div key={item.step} className="flex gap-3">
                      <div className="h-6 w-6 rounded-full bg-primary/10 flex items-center justify-center shrink-0 mt-0.5">
                        <span className="text-xs font-bold text-primary">{item.step}</span>
                      </div>
                      <div>
                        <p className="text-sm font-medium">{item.title}</p>
                        <p className="text-xs text-muted-foreground mt-0.5">{item.desc}</p>
                      </div>
                    </div>
                  ))}
                </div>

                <div className="rounded-lg bg-primary/5 border border-primary/20 p-3 mt-4">
                  <p className="text-xs text-muted-foreground">
                    <strong className="text-foreground">Why is this useful?</strong> Instantly prototype analytics dashboards with AI-generated data. Perfect for demos, POCs, and exploring what's possible with Databricks Genie.
                  </p>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                <p className="text-sm text-muted-foreground">
                  We'd love to hear from you. Share your thoughts, report issues, or suggest improvements.
                </p>

                <textarea
                  className="w-full h-32 px-3 py-2 rounded-md border bg-background text-sm resize-none focus:outline-none focus:ring-1 focus:ring-primary"
                  placeholder="What's on your mind? Share your feedback here..."
                  value={feedbackText}
                  onChange={(e) => setFeedbackText(e.target.value)}
                  disabled={submitFeedback.isPending}
                />

                {submitted && (
                  <div className="flex items-center gap-2 text-sm text-emerald-600 dark:text-emerald-400">
                    <CheckCircle2 className="h-4 w-4" />
                    Thank you! Your feedback has been submitted.
                  </div>
                )}

                <Button
                  className="w-full gap-2"
                  onClick={handleSubmitFeedback}
                  disabled={!feedbackText.trim() || submitFeedback.isPending}
                >
                  {submitFeedback.isPending ? (
                    <><Loader2 className="h-4 w-4 animate-spin" /> Submitting...</>
                  ) : (
                    <><Send className="h-4 w-4" /> Submit Feedback</>
                  )}
                </Button>
              </div>
            )}
          </div>
        </Card>
      </div>
    </>
  );
}
