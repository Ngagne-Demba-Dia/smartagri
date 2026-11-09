import type { ReactNode } from "react";

export interface Column<T> {
  key: string;
  header: string;
  cell: (row: T) => ReactNode;
  /** Colonne numérique : alignée à droite. */
  numeric?: boolean;
}

/** Tableau accessible (légende, en-têtes de colonne et de ligne) qui défile seul sur petit écran. */
export function DataTable<T>({
  caption,
  columns,
  rows,
  rowKey,
  captionHidden = false,
}: {
  caption: string;
  columns: ReadonlyArray<Column<T>>;
  rows: readonly T[];
  rowKey: (row: T) => string;
  captionHidden?: boolean;
}) {
  return (
    <div className="card relative overflow-x-auto p-0">
      <table className="w-full border-collapse text-left">
        <caption className={captionHidden ? "sr-only" : "px-4 pt-3 text-left font-semibold"}>
          {caption}
        </caption>
        <thead>
          <tr className="border-b border-line bg-surface text-sm text-mute">
            {columns.map((c) => (
              <th
                key={c.key}
                scope="col"
                className={`px-4 py-2 font-semibold ${c.numeric ? "text-right" : ""}`}
              >
                {c.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={rowKey(row)} className="border-b border-line transition-colors last:border-0 hover:bg-surface">
              {columns.map((c, i) =>
                i === 0 ? (
                  <th key={c.key} scope="row" className="px-4 py-3 font-semibold">
                    {c.cell(row)}
                  </th>
                ) : (
                  <td key={c.key} className={`px-4 py-3 ${c.numeric ? "text-right tabular-nums" : ""}`}>
                    {c.cell(row)}
                  </td>
                ),
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
