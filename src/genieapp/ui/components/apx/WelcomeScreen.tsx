/**
 * Welcome screen with sample questions as clickable cards.
 */

import { Card, CardContent } from "@/components/ui/card";
import { MessageSquare, Sparkles } from "lucide-react";

interface WelcomeScreenProps {
  displayName: string;
  sampleQuestions: string[];
  onSelectQuestion: (question: string) => void;
}

export function WelcomeScreen({
  displayName,
  sampleQuestions,
  onSelectQuestion,
}: WelcomeScreenProps) {
  return (
    <div className="flex flex-col items-center justify-center h-full px-4">
      <div className="flex items-center gap-2 mb-2">
        <Sparkles className="h-8 w-8 text-primary" />
        <h2 className="text-2xl font-bold">{displayName}</h2>
      </div>
      <p className="text-muted-foreground mb-8 text-center max-w-md">
        Ask questions about your data using natural language. Try one of these to get started:
      </p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-w-2xl w-full">
        {sampleQuestions.map((q) => (
          <Card
            key={q}
            className="cursor-pointer hover:bg-accent transition-colors"
            onClick={() => onSelectQuestion(q)}
          >
            <CardContent className="flex items-start gap-3 p-4">
              <MessageSquare className="h-5 w-5 text-muted-foreground shrink-0 mt-0.5" />
              <span className="text-sm">{q}</span>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
