import { useState, type ChangeEvent } from "react";
import { useQueryMutation } from "../../hooks";
import { useUIState } from "../../store";

export function QueryBox() {
  const { isDatasetActive } = useUIState();
  const [query, setQuery] = useState("");
  const [error, setError] = useState<string | null>(null);
  const mutation = useQueryMutation();

  const handleSubmit = async () => {
    const trimmed = query.trim();
    if (!trimmed) return;

    setError(null);
    try {
      await mutation.mutateAsync(trimmed);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Query failed. Please try again.";
      setError(message);
    }
  };

  const isQuerying = mutation.isPending;
  const canSubmit = isDatasetActive && query.trim().length > 0 && !isQuerying;

  return (
    <section className="bg-gradient-to-br from-white to-indigo-50/50 rounded-xl border border-indigo-200 p-6 shadow-sm">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">Query</h2>
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Ask a question about your dataset
          </label>
          <textarea
            placeholder="e.g., Show me the top 10 products by sales as a bar chart"
            rows={4}
            value={query}
            onChange={(e: ChangeEvent<HTMLTextAreaElement>) => setQuery(e.target.value)}
            disabled={!isDatasetActive || isQuerying}
            className="w-full border border-gray-300 rounded-md p-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent disabled:bg-gray-50 disabled:text-gray-500 disabled:cursor-not-allowed"
          />
        </div>
        <button
          type="button"
          onClick={handleSubmit}
          disabled={!canSubmit}
          className="w-full bg-indigo-600 text-white rounded-md px-4 py-2.5 text-sm font-medium hover:bg-indigo-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
        >
          {isQuerying ? "Analyzing..." : "Analyze"}
        </button>
      </div>
      {error && (
        <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-md">
          <p className="text-sm text-red-800">{error}</p>
        </div>
      )}
    </section>
  );
}
