import os
import json
import requests
from datetime import datetime, timezone

API_KEY = os.environ["YOUTUBE_API_KEY"]

# 対象チャンネル（7つ分をここに入れる）
CHANNEL_IDS = [
    "UCgbQLx3kC5_i-0J_empIsxA",
    "UCSxorXiovSSaafcDp_JJAjg",
    "UCyBaf1pv1dO_GnkFBg1twLA",
    "UCsy_jJ1qOyhr7wA4iKiq4Iw",
    "UCrw103c53EKupQnNQGC4Gyw",
    "UC_kfGHWj4_7wbG3dBLnscRA",
    "UCPFrZbMFbZ47YO7OBnte_-Q",
]

OUTPUT_JSON = "data/streams.json"
OUTPUT_HTML = "index.html"


def fetch_videos(channel_id, status):
    """特定チャンネル・状態（upcoming/live/completed）の動画一覧を取得"""
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "channelId": channel_id,
        "eventType": status,
        "type": "video",
        "order": "date",
        "maxResults": 25,
        "key": API_KEY,
    }
    res = requests.get(url, params=params)
    res.raise_for_status()
    items = res.json().get("items", [])
    video_ids = [i["id"]["videoId"] for i in items if "id" in i]
    return video_ids


def fetch_video_details(video_ids):
    """videoIdリストから詳細情報（description含む）を取得"""
    if not video_ids:
        return []
    url = "https://www.googleapis.com/youtube/v3/videos"
    params = {
        "part": "snippet,liveStreamingDetails",
        "id": ",".join(video_ids),
        "key": API_KEY,
    }
    res = requests.get(url, params=params)
    res.raise_for_status()
    items = res.json().get("items", [])
    videos = []
    for item in items:
        snippet = item.get("snippet", {})
        live = item.get("liveStreamingDetails", {})
        videos.append({
            "id": item["id"],
            "title": snippet.get("title", ""),
            "channel": snippet.get("channelTitle", ""),
            "channel_id": snippet.get("channelId", ""),
            "description": snippet.get("description", ""),
            "thumbnail": snippet.get("thumbnails", {}).get("medium", {}).get("url", ""),
            "url": f"https://www.youtube.com/watch?v={item['id']}",
            "scheduled": live.get("scheduledStartTime", ""),
            "status": snippet.get("liveBroadcastContent", ""),  # 'live', 'upcoming', 'none'
        })
    return videos


    def collect_all_streams():
        all_streams = {"live": [], "upcoming": [], "completed": []}
    
        for cid in CHANNEL_IDS:
            for status in ["live", "upcoming", "completed"]:
                video_ids = fetch_videos(cid, status if status != "completed" else "completed")
                details = fetch_video_details(video_ids)
                for v in details:
                    if status == "completed" and v["status"] == "none":
                        v["status"] = "completed"
                    all_streams[v["status"]].append(v)

    # 🔽 ここで各カテゴリ内を時間順ソートにする！
    for key in all_streams:
        all_streams[key].sort(
            key=lambda x: x.get("scheduled", "") or "9999-99-99T99:99:99Z"
        )

    return all_streams



def save_json(data):
    os.makedirs("data", exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def generate_html(data):
    html = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<title>YouTube 配信スケジュール</title>
<style>
body {
  font-family: "Noto Sans JP", sans-serif;
  background: #f8f8f8;
  margin: 0;
  color: #222;
}
h1 {
  text-align: center;
  padding: 1.2em 0;
  margin: 0;
  font-size: 1.6rem;
  background: #fff;
  box-shadow: 0 1px 4px rgba(0,0,0,0.05);
}

.section {
  width: 100%;
  max-width: 1280px;
  margin: 30px auto;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 6px rgba(0,0,0,0.05);
  overflow: hidden;
}
.section-header {
  padding: 16px 20px;
  font-size: 18px;
  font-weight: 600;
  cursor: pointer;
  border-bottom: 1px solid #eee;
  transition: background 0.2s;
}
.section-header:hover {
  background: #f5f5f5;
}
.section-content {
  display: none;
  padding: 20px;
  gap: 20px;
  justify-content: center;
  flex-wrap: wrap;
  background: #fafafa;
}

.card {
  width: 290px;
  height: 440px;
  background: #fff;
  border-radius: 10px;
  overflow: hidden;
  box-shadow: 0 2px 5px rgba(0,0,0,0.1);
  display: flex;
  flex-direction: column;
  transition: transform 0.15s ease;
}
.card:hover {
  transform: translateY(-4px);
}
.thumb {
  width: 100%;
  height: 170px;
  object-fit: cover;
}
.info {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 12px 14px;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: #ccc transparent;
}
.info::-webkit-scrollbar { width: 6px; }
.info::-webkit-scrollbar-thumb {
  background: #ccc;
  border-radius: 3px;
}
.channel {
  font-size: 13px;
  font-weight: 600;
  color: #0070f3;
  margin-bottom: 4px;
}
h3 {
  font-size: 14px;
  margin: 4px 0 6px;
  font-weight: 500;
  line-height: 1.4;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}
.time {
  font-size: 12px;
  color: #666;
  margin-bottom: 6px;
}
.desc {
  font-size: 13px;
  line-height: 1.5;
  color: #444;
  white-space: pre-wrap;
}

</style>
<script>
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".section-header").forEach(btn => {
    btn.addEventListener("click", () => {
      const content = btn.nextElementSibling;
      content.style.display = (content.style.display === "flex") ? "none" : "flex";
    });
  });
});
</script>
</head>
<body>
<h1>配信スケジュール（7チャンネル）</h1>
"""

    sections = [("live", "🔴 配信中"), ("upcoming", "⏰ 配信予定"), ("completed", "📼 アーカイブ")]
    for key, label in sections:
        html += f'<div class="section"><div class="section-header">{label}</div><div class="section-content">'
        for s in data.get(key, []):
            date = s.get("scheduled", "")
            if date:
                dt = datetime.fromisoformat(date.replace("Z", "+00:00")).astimezone(timezone.utc)
                date_str = dt.strftime("%Y-%m-%d %H:%M UTC")
            else:
                date_str = "日時不明"
            html += f"""
  <div class="card">
    <a href="{s['url']}" target="_blank"><img src="{s['thumbnail']}" class="thumb"></a>
    <div class="info">
      <p class="channel">{s['channel']}</p>
      <h3>{s['title']}</h3>
      <p class="time">{date_str}</p>
      <div class="desc">{s['description']}</div>
    </div>
  </div>
"""
        html += "</div></div>"

    html += "</body></html>"

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)


if __name__ == "__main__":
    data = collect_all_streams()
    save_json(data)
    generate_html(data)
    print("✅ 配信データを更新し、HTMLを生成しました！")


