import { useState } from "react";
import IngestForm from "./components/IngestForm";
import VideoCards from "./components/VideoCards";
import ChatPanel from "./components/ChatPanel";
import "./App.css";

function App() {
  const [sessionId] = useState(() => crypto.randomUUID());
  const [videoData, setVideoData] = useState(null);
  const [loading, setLoading] = useState(false);

  return (
    <div className="app">
      <h1>🎬 Creator RAG</h1>
      <IngestForm
        sessionId={sessionId}
        setVideoData={setVideoData}
        setLoading={setLoading}
        loading={loading}
      />
      {videoData && (
        <>
          <VideoCards videoData={videoData} />
          <ChatPanel sessionId={sessionId} />
        </>
      )}
    </div>
  );
}

export default App;