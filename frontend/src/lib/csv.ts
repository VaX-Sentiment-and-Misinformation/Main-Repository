export type CsvCell = string | number | undefined;

// RFC 4180: quote a cell only when it holds a quote, comma or newline; missing values stay empty
const cell = (v: CsvCell) => {
  const s = v === undefined ? "" : String(v);
  return /[",\r\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
};

export function toCsv(rows: CsvCell[][]): string {
  return rows.map((r) => r.map(cell).join(",")).join("\r\n");
}

// The BOM makes Excel read the file as UTF-8 rather than the system codepage
export function downloadCsv(filename: string, rows: CsvCell[][]) {
  const url = URL.createObjectURL(new Blob(["﻿" + toCsv(rows)], { type: "text/csv;charset=utf-8" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  // Revoking in the same tick can cancel the download in some browsers
  setTimeout(() => URL.revokeObjectURL(url), 0);
}
