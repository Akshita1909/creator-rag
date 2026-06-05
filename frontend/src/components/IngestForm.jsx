import { useState } from "react";
import axios from "axios";

function IngestForm({ sessionId, setVideoData, setLoading, loading }) {
  const [urlA, setUrlA] = useState("");
  const [urlB, setUrlB] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = async () => {
    if (!urlA || !urlB) {
      setError("Please enter both URLs");
      return;
    }
    setError("");
    setLoading(true);
    try {
      const res = await axios.post("http://localhost:8000/ingest", {
        url_a: urlA,
        url_b: urlB,
        session_id: sessionId,
      });
      setVideoData(res.data);
    } catch (e) {
      setError(e.response?.data?.detail || "Ingestion failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="ingest-form">
      <input
        type="text"
        placeholder="Video A URL (YouTube or Instagram)"
        value={urlA}
        onChange={(e) => setUrlA(e.target.value)}
      />
      <input
        type="text"
        placeholder="Video B URL (YouTube or Instagram)"
        value={urlB}
        onChange={(e) => setUrlB(e.target.value)}
      />
      <button onClick={handleSubmit} disabled={loading}>
        {loading ? "Ingesting..." : "Analyze Videos"}
      </button>
      {error && <p className="error">{error}</p>}
    </div>
  );
}

export default IngestForm;