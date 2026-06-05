import { useState, useRef, useEffect } from "react";

function ChatPanel({ sessionId }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim() || streaming) return;

    const userMsg = { role: "user", content: input };
    const currentInput = input;
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setStreaming(true);

    setMessages((prev) => [...prev, { role: "ai", content: "" }]);

    try {
      const res = await fetch("http://localhost:8000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, message: currentInput }),
      });

      const reader = res.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split("\n").filter((l) => l.startsWith("data: "));

        for (const line of lines) {
          try {
            const data = JSON.parse(line.replace("data: ", ""));
            if (data.token) {
              setMessages((prev) => {
                const updated = prev.map((msg, i) =>
                  i === prev.length - 1
                    ? { ...msg, content: msg.content + data.token }
                    : msg
                );
                return updated;
              });
            }
            if (data.done) setStreaming(false);
          } catch {
            // skip malformed chunks
          }
        }
      }
    } catch (e) {
      setMessages((prev) =>
        prev.map((msg, i) =>
          i === prev.length - 1
            ? { ...msg, content: "Error: " + e.message }
            : msg
        )
      );
      setStreaming(false);
    }
  };

  return (
    <div className="chat-panel">
      <h2>Chat</h2>
      <div className="chat-messages">
        {messages.map((msg, i) => (
          <div key={i} className={`message ${msg.role}`}>
            <strong>{msg.role === "user" ? "You" : "AI"}:</strong> {msg.content}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
      <div className="chat-input">
        <input
          type="text"
          placeholder="Ask about the videos..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && sendMessage()}
        />
        <button onClick={sendMessage} disabled={streaming}>
          {streaming ? "..." : "Send"}
        </button>
      </div>
    </div>
  );
}

export default ChatPanel;