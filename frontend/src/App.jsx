import { useEffect, useMemo, useState } from "react";

function formatSize(sizeBytes) {
  if (sizeBytes < 1024) {
    return `${sizeBytes} B`;
  }
  if (sizeBytes < 1024 * 1024) {
    return `${(sizeBytes / 1024).toFixed(1)} KB`;
  }
  return `${(sizeBytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function App() {
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [uploadDir, setUploadDir] = useState("D:\\data");
  const [status, setStatus] = useState("Ready");
  const [error, setError] = useState("");
  const [isUploading, setIsUploading] = useState(false);

  const totalSize = useMemo(
    () => selectedFiles.reduce((sum, file) => sum + file.size, 0),
    [selectedFiles]
  );

  async function fetchUploadedFiles() {
    try {
      const response = await fetch("/api/uploads");
      if (!response.ok) {
        throw new Error(`Failed to load uploads: ${response.status}`);
      }

      const data = await response.json();
      setUploadDir(data.upload_dir ?? "D:\\data");
      setUploadedFiles(data.files ?? []);
    } catch (err) {
      setError(err.message || "Could not load uploaded files.");
    }
  }

  useEffect(() => {
    fetchUploadedFiles();
  }, []);

  function onFileChange(event) {
    const files = Array.from(event.target.files ?? []);
    setSelectedFiles(files);
    setError("");

    if (files.length === 0) {
      setStatus("No files selected");
      return;
    }

    setStatus(`Selected ${files.length} file(s)`);
  }

  async function uploadSelectedFiles(event) {
    event.preventDefault();

    if (selectedFiles.length === 0) {
      setStatus("Please select at least one file");
      return;
    }

    setIsUploading(true);
    setError("");
    setStatus("Uploading...");

    try {
      const formData = new FormData();
      selectedFiles.forEach((file) => formData.append("files", file));

      const response = await fetch("/api/uploads", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Upload failed with status ${response.status}`);
      }

      const data = await response.json();
      const count = data.files?.length ?? 0;
      setStatus(`Upload complete: ${count} file(s) saved`);
      setSelectedFiles([]);
      await fetchUploadedFiles();
    } catch (err) {
      setError(err.message || "Upload failed.");
      setStatus("Upload failed");
    } finally {
      setIsUploading(false);
    }
  }

  return (
    <main className="app">
      <h1>Local File Upload</h1>
      <p className="hint">
        Upload files from desktop or phone. Files are stored in <code>{uploadDir}</code>.
      </p>

      <form className="upload-form" onSubmit={uploadSelectedFiles}>
        <input type="file" multiple onChange={onFileChange} />

        <button type="submit" disabled={isUploading}>
          {isUploading ? "Uploading..." : "Upload Files"}
        </button>
      </form>

      <p className="status">{status}</p>
      {selectedFiles.length > 0 && (
        <p className="hint">
          {selectedFiles.length} selected, total size {formatSize(totalSize)}
        </p>
      )}
      {error && <p className="error">{error}</p>}

      <section className="uploaded-files">
        <h2>Uploaded Files</h2>
        {uploadedFiles.length === 0 ? (
          <p className="hint">No uploads yet.</p>
        ) : (
          <ul>
            {uploadedFiles.map((name) => (
              <li key={name}>{name}</li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
