/**
 * Compact table schema viewer for inline sidebar display.
 */

import { useTableDetail } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";

interface TableDetailPanelProps {
  tableName: string;
}

/** Map SQL types to color classes. */
function typeColor(type: string): string {
  const t = type.toLowerCase();
  if (t.includes("int") || t.includes("long") || t.includes("short") || t.includes("byte"))
    return "bg-blue-100 text-blue-700 border-blue-200 dark:bg-blue-950 dark:text-blue-300 dark:border-blue-800";
  if (t.includes("double") || t.includes("float") || t.includes("decimal") || t.includes("numeric"))
    return "bg-cyan-100 text-cyan-700 border-cyan-200 dark:bg-cyan-950 dark:text-cyan-300 dark:border-cyan-800";
  if (t.includes("string") || t.includes("varchar") || t.includes("char") || t.includes("text"))
    return "bg-emerald-100 text-emerald-700 border-emerald-200 dark:bg-emerald-950 dark:text-emerald-300 dark:border-emerald-800";
  if (t.includes("date") || t.includes("time") || t.includes("timestamp"))
    return "bg-violet-100 text-violet-700 border-violet-200 dark:bg-violet-950 dark:text-violet-300 dark:border-violet-800";
  if (t.includes("bool"))
    return "bg-amber-100 text-amber-700 border-amber-200 dark:bg-amber-950 dark:text-amber-300 dark:border-amber-800";
  if (t.includes("binary") || t.includes("array") || t.includes("map") || t.includes("struct"))
    return "bg-rose-100 text-rose-700 border-rose-200 dark:bg-rose-950 dark:text-rose-300 dark:border-rose-800";
  return "bg-gray-100 text-gray-600 border-gray-200 dark:bg-gray-800 dark:text-gray-400 dark:border-gray-700";
}

export function TableDetailPanel({ tableName }: TableDetailPanelProps) {
  const { data: detail, isLoading } = useTableDetail(tableName);

  if (isLoading) {
    return (
      <div className="space-y-1.5 py-1">
        <Skeleton className="h-3 w-3/4" />
        <Skeleton className="h-3 w-1/2" />
        <Skeleton className="h-3 w-2/3" />
      </div>
    );
  }

  if (!detail) {
    return <p className="text-xs text-muted-foreground py-1">Not found.</p>;
  }

  return (
    <div className="space-y-1">
      {detail.comment && (
        <p className="text-xs text-muted-foreground italic">{detail.comment}</p>
      )}
      {detail.columns.map((col) => (
        <div
          key={col.name}
          className="flex items-center gap-1.5 py-0.5"
        >
          <span className="text-xs font-mono truncate">{col.name}</span>
          <Badge
            variant="outline"
            className={`text-[10px] font-mono px-1 py-0 h-4 shrink-0 ${typeColor(col.type)}`}
          >
            {col.type}
          </Badge>
        </div>
      ))}
    </div>
  );
}
