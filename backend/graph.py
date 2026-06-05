import os
from typing import TypedDict, Annotated, List
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv

load_dotenv()

chroma_client = chromadb.EphemeralClient()
embedder = embedding_functions.DefaultEmbeddingFunction()
collection = chroma_client.get_or_create_collection(
    "videos",
    embedding_function=embedder
)

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    groq_api_key=os.getenv("GROQ_API_KEY"),
    streaming=True,
    temperature=0.3,
)


class AgentState(TypedDict):
    messages: Annotated[List, add_messages]
    video_metadata: dict
    retrieved_context: str


def retrieve_node(state: AgentState) -> AgentState:
    last_message = state["messages"][-1].content

    results = collection.query(
        query_texts=[last_message],
        n_results=6,
        include=["documents", "metadatas", "distances"]
    )

    context_parts = []
    if results["documents"] and results["documents"][0]:
        for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
            vid = meta.get("video_id", "?")
            context_parts.append(f"[Video {vid}]: {doc}")

    state["retrieved_context"] = "\n\n".join(context_parts)
    return state


def generate_node(state: AgentState) -> AgentState:
    metadata = state.get("video_metadata", {})
    meta_a = metadata.get("A", {})
    meta_b = metadata.get("B", {})

    system_prompt = f"""You are an expert social media analytics assistant helping creators understand their video performance.

VIDEO METADATA:
Video A — Title: {meta_a.get('title','N/A')} | Creator: {meta_a.get('creator','N/A')} | Platform: {meta_a.get('platform','N/A')}
Views: {meta_a.get('views',0):,} | Likes: {meta_a.get('likes',0):,} | Comments: {meta_a.get('comments',0):,}
Engagement Rate: {meta_a.get('engagement_rate',0)}% | Followers: {meta_a.get('follower_count',0):,}
Duration: {meta_a.get('duration',0)}s | Upload Date: {meta_a.get('upload_date','N/A')}
Hashtags: {', '.join(meta_a.get('hashtags',[])[:5])}

Video B — Title: {meta_b.get('title','N/A')} | Creator: {meta_b.get('creator','N/A')} | Platform: {meta_b.get('platform','N/A')}
Views: {meta_b.get('views',0):,} | Likes: {meta_b.get('likes',0):,} | Comments: {meta_b.get('comments',0):,}
Engagement Rate: {meta_b.get('engagement_rate',0)}% | Followers: {meta_b.get('follower_count',0):,}
Duration: {meta_b.get('duration',0)}s | Upload Date: {meta_b.get('upload_date','N/A')}
Hashtags: {', '.join(meta_b.get('hashtags',[])[:5])}

RETRIEVED TRANSCRIPT CONTEXT:
{state.get('retrieved_context', 'No context retrieved.')}

Rules:
- Always cite which video chunk you are referencing like [Video A] or [Video B]
- Be specific, use the actual numbers from metadata
- Compare directly when asked
- Keep responses concise but insightful
"""

    messages = [SystemMessage(content=system_prompt)] + state["messages"]
    response = llm.invoke(messages)
    state["messages"] = state["messages"] + [response]
    return state


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("generate", generate_node)
    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", END)
    return graph.compile()


rag_graph = build_graph()