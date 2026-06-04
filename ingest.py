import os, re, json, httpx
from youtube_transcript_api import YouTubeTranscriptApi
from yt_dlp import YoutubeDL
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()

chroma_client = chromadb.PersistentClient(path="./chroma_store")
collection = chroma_client.get_or_create_collection("videos")

embedder = SentenceTransformer("all-MiniLM-L6-v2")


def extract_youtube_id(url: str) -> str:
    match = re.search(r"(?:v=|youtu\.be/)([a-zA-Z0-9_-]{11})", url)
    return match.group(1) if match else None


def get_youtube_metadata(url: str) -> dict:
    ydl_opts = {"quiet": True, "skip_download": True}
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return {
            "title": info.get("title", ""),
            "creator": info.get("uploader", ""),
            "views": info.get("view_count", 0),
            "likes": info.get("like_count", 0),
            "comments": info.get("comment_count", 0),
            "upload_date": info.get("upload_date", ""),
            "duration": info.get("duration", 0),
            "hashtags": info.get("tags", [])[:10],
            "follower_count": info.get("channel_follower_count", 0),
            "platform": "youtube",
        }


def get_youtube_transcript(video_id: str) -> str:
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join([t["text"] for t in transcript])
    except Exception:
        return ""


def get_instagram_metadata(url: str) -> dict:
    ydl_opts = {"quiet": True, "skip_download": True}
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                "title": info.get("title", info.get("description", "Instagram Reel")[:80]),
                "creator": info.get("uploader", info.get("channel", "")),
                "views": info.get("view_count", 0),
                "likes": info.get("like_count", 0),
                "comments": info.get("comment_count", 0),
                "upload_date": info.get("upload_date", ""),
                "duration": info.get("duration", 0),
                "hashtags": re.findall(r"#\w+", info.get("description", "")),
                "follower_count": info.get("channel_follower_count", 0),
                "platform": "instagram",
            }
    except Exception as e:
        return {
            "title": "Instagram Reel",
            "creator": "Unknown",
            "views": 0, "likes": 0, "comments": 0,
            "upload_date": "", "duration": 0,
            "hashtags": [], "follower_count": 0,
            "platform": "instagram",
            "error": str(e)
        }


def get_instagram_transcript(url: str) -> str:
    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "writeautomaticsub": True,
        "subtitlesformat": "json3",
    }
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            desc = info.get("description", "")
            return desc if desc else "[No transcript available for this Instagram Reel]"
    except Exception:
        return "[No transcript available for this Instagram Reel]"


def chunk_text(text: str, chunk_size: int = 300, overlap: int = 50) -> list[str]:
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        if chunk:
            chunks.append(chunk)
    return chunks


def compute_engagement_rate(meta: dict) -> float:
    views = meta.get("views", 0)
    likes = meta.get("likes", 0)
    comments = meta.get("comments", 0)
    if views == 0:
        # Instagram doesn't expose view count via scraping
        # Return raw likes+comments as engagement score instead
        return round(likes + comments, 4)
    return round(((likes + comments) / views) * 100, 4)


def ingest_video(url: str, video_id: str) -> dict:
    is_youtube = "youtube.com" in url or "youtu.be" in url

    if is_youtube:
        yt_id = extract_youtube_id(url)
        metadata = get_youtube_metadata(url)
        transcript = get_youtube_transcript(yt_id) if yt_id else ""
    else:
        metadata = get_instagram_metadata(url)
        transcript = get_instagram_transcript(url)

    metadata["engagement_rate"] = compute_engagement_rate(metadata)
    metadata["url"] = url
    metadata["video_id"] = video_id

    if transcript:
        chunks = chunk_text(transcript)
        embeddings = embedder.encode(chunks).tolist()

        try:
            existing = collection.get(where={"video_id": video_id})
            if existing["ids"]:
                collection.delete(ids=existing["ids"])
        except Exception:
            pass

        ids = [f"{video_id}_chunk_{i}" for i in range(len(chunks))]
        collection.add(
            documents=chunks,
            embeddings=embeddings,
            ids=ids,
            metadatas=[{"video_id": video_id, **{k: str(v) for k, v in metadata.items()}} for _ in chunks]
        )

    return {
        "metadata": metadata,
        "transcript": transcript,
        "chunks_stored": len(chunk_text(transcript)) if transcript else 0
    }