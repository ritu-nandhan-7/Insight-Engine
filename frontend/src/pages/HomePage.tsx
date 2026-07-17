import { Layout } from "../components/layout";
import { Upload } from "../components/upload";
import { DatasetSummary } from "../components/dataset";
import { QueryBox } from "../components/query";
import { Chart } from "../components/chart";

export function HomePage() {
  return (
    <Layout>
      <Upload />
      <DatasetSummary />
      <QueryBox />
      <Chart />
    </Layout>
  );
}
