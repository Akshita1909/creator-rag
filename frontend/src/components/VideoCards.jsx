function VideoCard({ label, meta }) {
  return (
    <div className="video-card">
      <h2>Video {label}</h2>
      <h3>{meta.title}</h3>
      <p><strong>Creator:</strong> {meta.creator}</p>
      <p><strong>Platform:</strong> {meta.platform}</p>
      <p><strong>Views:</strong> {meta.views?.toLocaleString()}</p>
      <p><strong>Likes:</strong> {meta.likes?.toLocaleString()}</p>
      <p><strong>Comments:</strong> {meta.comments?.toLocaleString()}</p>
      <p><strong>Engagement Rate:</strong> {meta.engagement_rate}{meta.platform === "instagram" && meta.views === 0 ? " (likes+comments)" : "%"}</p>
      <p><strong>Followers:</strong> {meta.follower_count?.toLocaleString()}</p>
      <p><strong>Duration:</strong> {meta.duration}s</p>
      <p><strong>Upload Date:</strong> {meta.upload_date}</p>
      <p><strong>Hashtags:</strong> {meta.hashtags?.slice(0, 5).join(", ")}</p>
    </div>
  );
}

function VideoCards({ videoData }) {
  return (
    <div className="video-cards">
      <VideoCard label="A" meta={videoData.video_a} />
      <VideoCard label="B" meta={videoData.video_b} />
    </div>
  );
}

export default VideoCards;