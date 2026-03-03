/**
 * Chat message bubble — renders user question + Genie response.
 * Includes collapsible SQL, chart, data table, feedback, suggestions, and export.
 */

import { useState } from "react";
import {
  ChevronDown,
  ChevronRight,
  Code2,
  User,
  Copy,
  Check,
  BarChart3,
  ThumbsUp,
  ThumbsDown,
  AlertTriangle,
  HelpCircle,
} from "lucide-react";
import Markdown from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ChartRenderer } from "./ChartRenderer";
import { DataTable } from "./DataTable";
import { ExportButton } from "./ExportButton";
import { useSendFeedback, type ChatMessageOut } from "@/lib/api";

interface MessageBubbleProps {
  question: string;
  response: ChatMessageOut;
  onAskQuestion?: (question: string) => void;
}

/** Minimal component overrides for react-markdown. */
const mdComponents = {
  p: ({ children }: { children?: React.ReactNode }) => <p className="mb-1 last:mb-0">{children}</p>,
  strong: ({ children }: { children?: React.ReactNode }) => <strong className="font-semibold">{children}</strong>,
  ul: ({ children }: { children?: React.ReactNode }) => <ul className="list-disc pl-4 mb-1 space-y-0.5">{children}</ul>,
  ol: ({ children }: { children?: React.ReactNode }) => <ol className="list-decimal pl-4 mb-1 space-y-0.5">{children}</ol>,
  li: ({ children }: { children?: React.ReactNode }) => <li>{children}</li>,
  code: ({ children }: { children?: React.ReactNode }) => (
    <code className="bg-muted px-1 py-0.5 rounded text-xs font-mono">{children}</code>
  ),
};

const ERROR_MESSAGES: Record<string, string> = {
  PERMISSION_DENIED: "You don't have access to query this data.",
  NOT_FOUND: "The requested resource was not found.",
  TIMEOUT: "The query took too long. Try a simpler question.",
  RATE_LIMITED: "Too many requests. Please wait a moment.",
};

export function MessageBubble({ question, response, onAskQuestion }: MessageBubbleProps) {
  const [sqlExpanded, setSqlExpanded] = useState(false);
  const [chartVisible, setChartVisible] = useState(false);
  const [copied, setCopied] = useState(false);
  const [feedbackGiven, setFeedbackGiven] = useState<"POSITIVE" | "NEGATIVE" | null>(null);
  const sendFeedback = useSendFeedback();

  const copySQL = () => {
    if (response.sql) {
      navigator.clipboard.writeText(response.sql);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleFeedback = (rating: "POSITIVE" | "NEGATIVE") => {
    if (feedbackGiven) return;
    setFeedbackGiven(rating);
    sendFeedback.mutate({
      conversation_id: response.conversation_id,
      message_id: response.message_id,
      rating,
    });
  };

  const errorMessage = response.error_type && ERROR_MESSAGES[response.error_type]
    ? ERROR_MESSAGES[response.error_type]
    : response.error;

  return (
    <div className="space-y-3">
      {/* User question */}
      <div className="flex justify-end">
        <div className="flex items-start gap-2 max-w-[80%]">
          <div className="bg-primary text-primary-foreground rounded-2xl rounded-tr-sm px-4 py-2.5">
            <p className="text-sm">{question}</p>
          </div>
          <div className="shrink-0 w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
            <User className="h-4 w-4" />
          </div>
        </div>
      </div>

      {/* Genie response */}
      <div className="flex justify-start">
        <Card className="max-w-[85%] overflow-hidden">
          <div className="p-4 space-y-3">
            {/* Error */}
            {response.error && (
              <Badge variant="destructive">{errorMessage}</Badge>
            )}

            {/* Clarification — distinct styling */}
            {response.is_clarification && response.description ? (
              <div className="flex items-start gap-2 rounded-lg bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 p-3">
                <HelpCircle className="h-4 w-4 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
                <div className="text-sm text-amber-900 dark:text-amber-200">
                  <Markdown components={mdComponents}>{response.description}</Markdown>
                </div>
              </div>
            ) : (
              /* Description */
              response.description && (
                <div className="text-sm">
                  <Markdown components={mdComponents}>{response.description}</Markdown>
                </div>
              )
            )}

            {/* Query description */}
            {response.query_description && (
              <p className="text-xs text-muted-foreground italic">
                {response.query_description}
              </p>
            )}

            {/* SQL toggle */}
            {response.sql && (
              <div>
                <Button
                  variant="ghost"
                  size="sm"
                  className="gap-1 text-xs text-muted-foreground"
                  onClick={() => setSqlExpanded(!sqlExpanded)}
                >
                  {sqlExpanded ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
                  <Code2 className="h-3 w-3" />
                  SQL Query
                </Button>
                {sqlExpanded && (
                  <div className="relative mt-1 rounded-md overflow-hidden">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="absolute top-1 right-1 h-7 w-7 z-10 text-muted-foreground hover:text-foreground"
                      onClick={copySQL}
                    >
                      {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
                    </Button>
                    <SyntaxHighlighter
                      language="sql"
                      style={oneDark}
                      customStyle={{
                        margin: 0,
                        borderRadius: "0.375rem",
                        fontSize: "0.75rem",
                        padding: "0.75rem",
                      }}
                      wrapLongLines
                    >
                      {response.sql}
                    </SyntaxHighlighter>
                  </div>
                )}
              </div>
            )}

            {/* Truncation warning */}
            {response.is_truncated && (
              <div className="flex items-center gap-2 rounded-md bg-yellow-50 dark:bg-yellow-950/30 border border-yellow-200 dark:border-yellow-800 px-3 py-2">
                <AlertTriangle className="h-3.5 w-3.5 text-yellow-600 dark:text-yellow-400 shrink-0" />
                <span className="text-xs text-yellow-800 dark:text-yellow-300">
                  Results truncated — only showing first {response.row_count} rows.
                </span>
              </div>
            )}

            {/* Visualize button + Chart */}
            {response.columns.length >= 2 && response.data.length > 0 && (
              chartVisible ? (
                <ChartRenderer
                  suggestion={
                    response.chart_suggestion &&
                    response.chart_suggestion.chart_type !== "table"
                      ? response.chart_suggestion
                      : {
                          chart_type: "bar",
                          x_axis: response.columns[0],
                          y_axis: response.columns[1],
                          title: "",
                        }
                  }
                  data={response.data}
                  columns={response.columns}
                />
              ) : (
                <Button
                  variant="outline"
                  size="sm"
                  className="gap-1.5 text-xs"
                  onClick={() => setChartVisible(true)}
                >
                  <BarChart3 className="h-3.5 w-3.5" />
                  Visualize
                </Button>
              )
            )}

            {/* Data table */}
            {response.columns.length > 0 && response.data.length > 0 && (
              <DataTable
                columns={response.columns}
                data={response.data}
                className="max-h-64 border rounded-md"
              />
            )}

            {/* Footer: row count + feedback + export */}
            {(response.row_count > 0 || response.message_id) && (
              <div className="flex items-center justify-between pt-1">
                <div className="flex items-center gap-3">
                  {response.row_count > 0 && (
                    <span className="text-xs text-muted-foreground">
                      {response.row_count} row{response.row_count !== 1 ? "s" : ""}
                    </span>
                  )}
                  {/* Feedback buttons */}
                  {response.message_id && (
                    <div className="flex items-center gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        className={`h-6 w-6 ${feedbackGiven === "POSITIVE" ? "text-green-600" : "text-muted-foreground"}`}
                        onClick={() => handleFeedback("POSITIVE")}
                        disabled={!!feedbackGiven}
                      >
                        <ThumbsUp className={`h-3.5 w-3.5 ${feedbackGiven === "POSITIVE" ? "fill-current" : ""}`} />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className={`h-6 w-6 ${feedbackGiven === "NEGATIVE" ? "text-red-600" : "text-muted-foreground"}`}
                        onClick={() => handleFeedback("NEGATIVE")}
                        disabled={!!feedbackGiven}
                      >
                        <ThumbsDown className={`h-3.5 w-3.5 ${feedbackGiven === "NEGATIVE" ? "fill-current" : ""}`} />
                      </Button>
                    </div>
                  )}
                </div>
                {response.row_count > 0 && (
                  <ExportButton conversationId={response.conversation_id} />
                )}
              </div>
            )}

            {/* Suggested follow-up questions */}
            {response.suggested_questions.length > 0 && onAskQuestion && (
              <div className="flex flex-wrap gap-1.5 pt-1">
                {response.suggested_questions.map((q) => (
                  <Button
                    key={q}
                    variant="outline"
                    size="sm"
                    className="h-auto py-1 px-2.5 text-xs font-normal"
                    onClick={() => onAskQuestion(q)}
                  >
                    {q}
                  </Button>
                ))}
              </div>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}
