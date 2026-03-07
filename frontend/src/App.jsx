import { useEffect, useState } from "react";

export default function App() {
  const [message, setMessage] = useState("Loading...");
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();

    async function loadMessage() {
      try {
        const response = await fetch("/api/hello", {
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new Error(`Request failed with status ${response.status}`);
        }

        const data = await response.json();
        setMessage(data.message ?? "No message returned");
      } catch (err) {
        if (err.name !== "AbortError") {
          setError(err.message || "Unexpected error");
          setMessage("Unable to reach backend");
        }
      }
    }

    loadMessage();
    return () => controller.abort();
  }, []);

  return (
    <main className="app">
      <h1>FastAPI + React</h1>
      <p>{message}</p>
      {error && <p className="error">{error}</p>}
    </main>
  );
}
