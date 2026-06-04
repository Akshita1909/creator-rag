import os, json, asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from ingest import ingest_video
from graph import rag_graph, AgentState

load_dotenv()

app = FastAPI(title="Creator RAG API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

sessions: dict = {}


class IngestRequest(BaseModel):
    url_a: str
    url_b: str
    session_id: str


class ChatRequest(BaseModel):
    session_id: str
    message: str


@app.post("/ingest")
async def ingest_videos(req: IngestRequest):
    try:
        result_a = ingest_video(req.url_a, "A")
        result_b = ingest_video(req.url_b, "B")

        sessions[req.session_id] = {
            "video_metadata": {
                "A": result_a["metadata"],
                "B": result_b["metadata"],
            },
            "messages": [],
        }

        return {
            "status": "ok",
            "video_a": result_a["metadata"],
            "video_b": result_b["metadata"],
            "chunks_a": result_a["chunks_stored"],
            "chunks_b": result_b["chunks_stored"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat")
async def chat(req: ChatRequest):
    session = sessions.get(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found. Please ingest videos first.")

    session["messages"].append(HumanMessage(content=req.message))

    state: AgentState = {
        "messages": session["messages"],
        "video_metadata": session["video_metadata"],
        "retrieved_context": "",
    }

    async def stream_response():
        full_response = ""
        final_state = rag_graph.invoke(state)
        last_ai = final_state["messages"][-1]
        full_response = last_ai.content

        words = full_response.split(" ")
        for word in words:
            yield f"data: {json.dumps({'token': word + ' '})}\n\n"
            await asyncio.sleep(0.01)

        session["messages"] = final_state["messages"]
        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(stream_response(), media_type="text/event-stream")


@app.get("/session/{session_id}")
async def get_session(session_id: str):
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"video_metadata": session["video_metadata"]}


@app.get("/health")
async def health():
    return {"status": "ok"}