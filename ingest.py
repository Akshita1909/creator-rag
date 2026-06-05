import os, re
from youtube_transcript_api import YouTubeTranscriptApi
from yt_dlp import YoutubeDL
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

def extract_youtube_id(url):
    match = re.search(r"(?:v=|youtu\.be/)([a-zA-Z0-9_-]{11})", url)
    return match.group(1) if match else None

def get_youtube_metadata(url):
    with YoutubeDL({"quiet": True, "skip_download": True}) as ydl:
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

def get_youtube_transcript(video_id):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join([t["text"] for t in transcript])
    except Exception:
        return ""

def get_instagram_metadata(url):
    try:
        with YoutubeDL({"quiet": True, "skip_download": True}) as ydl:
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
            "title": "Instagram Reel", "creator": "Unknown",
            "views": 0, "likes": 0, "comments": 0,
            "upload_date": "", "duration": 0,
            "hashtags": [], "follower_count": 0,
            "platform": "instagram", "error": str(e)
        }

def get_instagram_transcript(url):
    try:
        with YoutubeDL({"quiet": True, "skip_download": True}) as ydl:
            info = ydl.extract_info(url, download=False)
            desc = info.get("description", "")
            return desc if desc else "[No transcript available]"
    except Exception:
        return "[No transcript available]"

def chunk_text(text, chunk_size=300, overlap=50):
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        if chunk:
            chunks.append(chunk)
    return chunks

def compute_engagement_rate(meta):
    views = meta.get("views", 0)
    if views == 0:
        return 0.0
    return round(((meta.get("likes", 0) + meta.get("comments", 0)) / views) * 100, 4)

def ingest_video(url, video_id):
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
        try:
            existing = collection.get(where={"video_id": video_id})
            if existing["ids"]:
                collection.delete(ids=existing["ids"])
        except Exception:
            pass
        ids = [f"{video_id}_chunk_{i}" for i in range(len(chunks))]
        collection.add(
            documents=chunks,
            ids=ids,
            metadatas=[{"video_id": video_id, **{k: str(v) for k, v in metadata.items()}} for _ in chunks]
        )

    return {
        "metadata": metadata,
        "transcript": transcript,
        "chunks_stored": len(chunk_text(transcript)) if transcript else 0
    }
