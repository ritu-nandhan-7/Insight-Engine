import type { ReactNode } from "react";

export function Layout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen">
      <header className="bg-white/90 backdrop-blur-md border-b border-white/20 shadow-lg">
        <div className="max-w-5xl mx-auto px-6 py-6 text-center">
          <h1 className="text-4xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent mb-2">
            Insight Engine
          </h1>
          <p className="text-base text-gray-700 max-w-2xl mx-auto">
            Transform your data into insights using AI. Upload any dataset, ask questions in plain English, and get beautiful visualizations instantly.
          </p>
        </div>
      </header>
      <main className="max-w-5xl mx-auto px-6 py-8">
        <div className="space-y-6">
          {children}
        </div>
      </main>
    </div>
  );
}
