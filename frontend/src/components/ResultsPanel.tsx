import { X, Download, ChevronLeft, ChevronRight } from 'lucide-react';
import { useState } from 'react';
import { useWorkflowStore } from '../store/workflowStore';

export default function ResultsPanel() {
  const { workflowResult, workflowId } = useWorkflowStore();
  const [page, setPage] = useState(0);
  const [isOpen, setIsOpen] = useState(true);

  if (!workflowResult || workflowResult.data.length === 0) {
    return null;
  }

  const pageSize = 10;
  const totalPages = Math.ceil(workflowResult.data.length / pageSize);
  const paginatedData = workflowResult.data.slice(
    page * pageSize,
    (page + 1) * pageSize
  );

  const handleDownload = async () => {
    if (!workflowId) return;

    try {
      // Create CSV content
      const headers = workflowResult.columns.join(',');
      const rows = workflowResult.data.map((row) =>
        workflowResult.columns
          .map((col) => {
            const val = row[col];
            if (val === null || val === undefined) return '';
            const str = String(val);
            // Escape quotes and wrap in quotes if contains comma
            if (str.includes(',') || str.includes('"') || str.includes('\n')) {
              return `"${str.replace(/"/g, '""')}"`;
            }
            return str;
          })
          .join(',')
      );
      const csv = [headers, ...rows].join('\n');

      // Download
      const blob = new Blob([csv], { type: 'text/csv' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'workflow_results.csv';
      a.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Failed to download:', error);
    }
  };

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-4 right-4 rounded-lg bg-block-green px-4 py-2 font-medium text-white shadow-lg hover:bg-block-green/90"
      >
        Show Results ({workflowResult.row_count} rows)
      </button>
    );
  }

  return (
    <div className="fixed bottom-0 left-64 right-0 z-40 border-t border-[#2a2a3a] bg-[#12121a] shadow-2xl">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[#2a2a3a] px-4 py-2">
        <div className="flex items-center gap-3">
          <h3 className="font-semibold text-white">Results</h3>
          <span className={`rounded-full px-2 py-0.5 text-xs ${
            workflowResult.is_partial 
              ? 'bg-orange-500/20 text-orange-400' 
              : 'bg-block-green/20 text-block-green'
          }`}>
            {workflowResult.row_count} rows{workflowResult.is_partial ? ' (partial)' : ''}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleDownload}
            className="flex items-center gap-1 rounded-lg border border-[#2a2a3a] px-3 py-1.5 text-sm text-white/70 hover:bg-white/5"
          >
            <Download size={14} />
            Download CSV
          </button>
          <button
            onClick={() => setIsOpen(false)}
            className="rounded p-1 hover:bg-white/10"
          >
            <X size={18} className="text-white/70" />
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="max-h-64 overflow-auto">
        <table className="w-full text-sm">
          <thead className="sticky top-0 bg-[#1a1a24]">
            <tr>
              {workflowResult.columns.map((col) => (
                <th
                  key={col}
                  className="whitespace-nowrap border-b border-[#2a2a3a] px-4 py-2 text-left font-medium text-white/70"
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {paginatedData.map((row, idx) => (
              <tr
                key={idx}
                className="border-b border-[#2a2a3a]/50 hover:bg-white/5"
              >
                {workflowResult.columns.map((col) => (
                  <td
                    key={col}
                    className="max-w-[200px] truncate px-4 py-2 text-white/80"
                    title={String(row[col] ?? '')}
                  >
                    {String(row[col] ?? '')}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between border-t border-[#2a2a3a] px-4 py-2">
          <span className="text-sm text-white/50">
            Page {page + 1} of {totalPages}
          </span>
          <div className="flex gap-1">
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0}
              className="rounded p-1 hover:bg-white/10 disabled:opacity-30"
            >
              <ChevronLeft size={18} className="text-white/70" />
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
              disabled={page === totalPages - 1}
              className="rounded p-1 hover:bg-white/10 disabled:opacity-30"
            >
              <ChevronRight size={18} className="text-white/70" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

