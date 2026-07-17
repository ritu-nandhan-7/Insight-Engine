import { useDatasetPreview, useDatasetSummary } from "../../hooks";

export function DatasetSummary() {
  const { data, isLoading, isError } = useDatasetSummary();
  const { data: preview } = useDatasetPreview();

  if (isLoading) {
    return (
      <section className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Dataset Information</h2>
        <p className="text-gray-500">Loading...</p>
      </section>
    );
  }

  if (isError || !data) {
    return (
      <section className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Dataset Information</h2>
        <p className="text-gray-500">No dataset loaded</p>
      </section>
    );
  }

  const formatBytes = (bytes: number) => {
    if (!bytes || bytes <= 0) return "N/A";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
  };

  return (
    <section className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">Dataset Information</h2>
      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-lg p-3 border border-blue-200">
          <p className="text-xs text-gray-600 mb-1">Rows</p>
          <p className="text-xl font-bold text-gray-900">{data.rows.toLocaleString()}</p>
        </div>
        <div className="bg-gradient-to-br from-purple-50 to-pink-50 rounded-lg p-3 border border-purple-200">
          <p className="text-xs text-gray-600 mb-1">Columns</p>
          <p className="text-xl font-bold text-gray-900">{data.columns}</p>
        </div>
        <div className="bg-gradient-to-br from-green-50 to-emerald-50 rounded-lg p-3 border border-green-200">
          <p className="text-xs text-gray-600 mb-1">File Size</p>
          <p className="text-xl font-bold text-gray-900">{formatBytes(data.file_size_bytes)}</p>
        </div>
        <div className="bg-gradient-to-br from-orange-50 to-amber-50 rounded-lg p-3 border border-orange-200">
          <p className="text-xs text-gray-600 mb-1">Memory Usage</p>
          <p className="text-xl font-bold text-gray-900">{formatBytes(data.memory_usage_bytes)}</p>
        </div>
      </div>
      {preview && preview.rows.length > 0 && (
        <div>
          <p className="text-sm font-medium text-gray-700 mb-2">
            Data Preview (first {preview.rows.length} of {preview.total_rows.toLocaleString()} rows)
          </p>
          <div className="overflow-x-auto border border-gray-200 rounded-lg">
            <table className="text-xs text-gray-700 w-full border-collapse">
              <thead>
                <tr className="bg-gray-50">
                  {preview.columns.map((col) => (
                    <th key={col} className="px-3 py-2 text-left font-semibold border-b border-gray-200 whitespace-nowrap">
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {preview.rows.map((row, ri) => (
                  <tr key={ri} className={ri % 2 === 0 ? "bg-white" : "bg-gray-50"}>
                    {row.map((cell, ci) => (
                      <td key={ci} className="px-3 py-1.5 border-b border-gray-200 whitespace-nowrap">
                        {cell === null ? <span className="text-gray-400 italic">null</span> : String(cell)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </section>
  );
}
