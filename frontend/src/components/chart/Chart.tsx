import { useEffect, useState } from "react";
import PlotlyChart from "react-plotly.js";
import type { PlotData, Layout, Config } from "plotly.js";
import { useQueryClient } from "@tanstack/react-query";
import { QUERY_KEY } from "../../hooks";
import type { EngineResult } from "../../types";

const PLOTLY_MODE_BAR: Partial<Config> = {
  toImageButtonOptions: {
    format: "png" as const,
    filename: "chart",
    height: 600,
    width: 900,
  },
  displayModeBar: true,
  displaylogo: false,
  modeBarButtonsToRemove: ["sendDataToCloud" as const],
};

export function Chart() {
  const queryClient = useQueryClient();
  const [results, setResults] = useState<EngineResult[]>([]);

  useEffect(() => {
    const unsubscribe = queryClient.getQueryCache().subscribe(() => {
      const cached = queryClient.getQueryData<EngineResult[]>(QUERY_KEY);
      if (cached) setResults(cached);
    });
    return unsubscribe;
  }, [queryClient]);

  if (results.length === 0) {
    return (
      <section className="bg-gradient-to-br from-white to-indigo-50/30 rounded-xl border border-indigo-200 p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Visualization</h2>
        <div className="text-center py-12">
          <p className="text-gray-500">No visualization yet. Ask a question to generate charts.</p>
        </div>
      </section>
    );
  }

  return (
    <section className="bg-gradient-to-br from-white to-indigo-50/30 rounded-xl border border-indigo-200 p-6 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-900">Visualization</h2>
        <span className="text-xs font-medium text-gray-700 bg-indigo-100 px-3 py-1.5 rounded-full border border-indigo-200">
          {results.length} chart{results.length !== 1 ? "s" : ""}
        </span>
      </div>
      <div className="space-y-6">
        {results.map((result, idx) => {
          const figure = result.figure as Record<string, unknown> | undefined;
          if (!figure || typeof figure !== "object") return null;

          const plotData = (figure.data as PlotData[]) ?? [];
          const layout = (figure.layout as Partial<Layout>) ?? {};

          return (
            <div key={result.timestamp + idx} className="border border-gray-200 rounded-lg overflow-hidden shadow-sm hover:shadow-md transition-shadow">
              <div className="bg-gray-50 px-4 py-3 border-b border-gray-200">
                <p className="text-sm font-medium text-gray-800">{result.query}</p>
                <p className="text-xs text-gray-600 mt-1">
                  {new Date(result.timestamp * 1000).toLocaleString()} • {result.execution_time_ms.toFixed(0)}ms
                </p>
              </div>
              <div className="p-4 bg-white">
                <PlotlyChart
                  data={plotData}
                  layout={layout}
                  config={PLOTLY_MODE_BAR}
                  style={{ width: "100%", height: "500px" }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
