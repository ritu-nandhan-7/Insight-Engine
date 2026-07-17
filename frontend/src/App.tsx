/**
 * App — root React component.
 *
 * Sets up React Query provider and renders the HomePage.
 */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { HomePage } from "./pages";

const queryClient = new QueryClient();

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <HomePage />
    </QueryClientProvider>
  );
}