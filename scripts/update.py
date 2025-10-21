import os
import json
import requests

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

def fetch_videos(channel_id, event_type):
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "channelId": channel_id,
        "eventType": event_type,
        "type": "video",
        "maxResults": 20,
        "order": "date",
        "key": API_KEY,
    }
    res = requests.get(url, params=params)
    res.raise_for_status()
    items = res.json().get("items", [])
    return [item["id"]["videoId"] for item in items if "id" in item]

def fetch_details(video_ids):
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
    videos = []
    for item in res.json().get("items", []):
        snippet = item["snippet"]
        live = item.get("liveStreamingDetails", {})
        videos.append({
            "id": item["id"],
            "title": snippet.get("title", ""),
            "channel": snippet.get("channelTitle", ""),
            "description": snippet.get("description", ""),
            "thumbnail": snippet.get("thumbnails", {}).get("medium", {}).get("url", ""),
            "url": f"https://www.youtube.com/watch?v={item['id']}",
            "scheduled": live.get("scheduledStartTime", ""),
            "status": snippet.get("liveBroadcastContent", "none")
        })
    return videos

def collect_all():
    data = {"live": [], "upcoming": [], "completed": []}
    for cid in CHANNEL_IDS:
        for etype in ["live", "upcoming", "completed"]:
            vids = fetch_videos(cid, etype)
            data[etype].extend(fetch_details(vids))
    return data

if __name__ == "__main__":
    data = collect_all()
    os.makedirs("data", exist_ok=True)
    with open("data/streams.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("✅ streams.json updated!")
