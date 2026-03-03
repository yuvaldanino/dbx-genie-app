/**
 * Tabular display of query results, capped at 100 rows.
 */

import { cn } from "@/lib/utils";

const MAX_DISPLAY_ROWS = 100;

interface DataTableProps {
  columns: string[];
  data: Record<string, string | number | null>[];
  className?: string;
}

export function DataTable({ columns, data, className }: DataTableProps) {
  if (!columns.length || !data.length) return null;

  const displayData = data.slice(0, MAX_DISPLAY_ROWS);
  const truncated = data.length > MAX_DISPLAY_ROWS;

  return (
    <div className={cn("w-full overflow-auto", className)}>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b bg-muted/50">
            {columns.map((col) => (
              <th
                key={col}
                className="px-3 py-2 text-left font-medium text-muted-foreground whitespace-nowrap"
              >
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {displayData.map((row, i) => (
            <tr key={i} className="border-b hover:bg-muted/30 transition-colors">
              {columns.map((col) => (
                <td key={col} className="px-3 py-2 whitespace-nowrap">
                  {row[col] != null ? String(row[col]) : "—"}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {truncated && (
        <p className="text-xs text-muted-foreground text-center mt-2">
          Showing {MAX_DISPLAY_ROWS} of {data.length} rows
        </p>
      )}
    </div>
  );
}
