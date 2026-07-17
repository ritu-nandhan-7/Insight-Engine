import { useState, useRef, type ChangeEvent } from "react";
import { useUploadMutation } from "../../hooks";

const ACCEPTED_FORMATS = ".csv,.xls,.xlsx,.json,.parquet";

export function Upload() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploadedName, setUploadedName] = useState<string | null>(null);
  const mutation = useUploadMutation();

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] ?? null;
    setSelectedFile(file);
    setError(null);
    setUploadedName(null);
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    try {
      await mutation.mutateAsync(selectedFile);
      setUploadedName(selectedFile.name);
      setSelectedFile(null);
      if (inputRef.current) inputRef.current.value = "";
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Upload failed. Please try again.";
      setError(message);
      setUploadedName(null);
    }
  };

  const isUploading = mutation.isPending;

  return (
    <section className="bg-gradient-to-br from-indigo-50 to-purple-50 rounded-xl border border-indigo-200 p-6 shadow-sm">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">Upload Dataset</h2>
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Select a file to analyze
          </label>
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPTED_FORMATS}
            onChange={handleFileChange}
            disabled={isUploading}
            className="block w-full text-sm text-gray-700 file:mr-4 file:py-2 file:px-4 file:border-0 file:rounded-md file:text-sm file:font-medium file:bg-indigo-600 file:text-white hover:file:bg-indigo-700 file:cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
          />
          <p className="mt-2 text-xs text-gray-600">
            Supported formats: CSV, Excel, JSON, Parquet
          </p>
        </div>
        <button
          type="button"
          onClick={handleUpload}
          disabled={!selectedFile || isUploading}
          className="w-full bg-indigo-600 text-white rounded-md px-4 py-2.5 text-sm font-medium hover:bg-indigo-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
        >
          {isUploading ? "Uploading..." : "Upload"}
        </button>
      </div>
      {uploadedName && (
        <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded-md">
          <p className="text-sm text-green-800 font-medium">
            Uploaded: {uploadedName}
          </p>
        </div>
      )}
      {selectedFile && !uploadedName && (
        <p className="mt-3 text-sm text-gray-600">
          Selected: <span className="font-medium">{selectedFile.name}</span>
        </p>
      )}
      {error && (
        <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-md">
          <p className="text-sm text-red-800">{error}</p>
        </div>
      )}
    </section>
  );
}
