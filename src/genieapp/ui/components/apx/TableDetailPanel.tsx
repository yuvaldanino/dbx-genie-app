/**
 * Compact table schema viewer for inline sidebar display.
 */

import { useTableDetail } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";

interface TableDetailPanelProps {
  tableName: string;
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
          <Badge variant="outline" className="text-[10px] font-mono px-1 py-0 h-4 shrink-0">
            {col.type}
          </Badge>
        </div>
      ))}
    </div>
  );
}
