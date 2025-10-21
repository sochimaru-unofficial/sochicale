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
    """指定チャンネルの配信情報を取得"""
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "channelId": channel_id,
        "type": "video",
        "maxResults": 20,
        "order": "date",
        "key": API_KEY,
    }

    # 🩹 completedのときは eventType を付けない（403対策）
    if event_type in ["live", "upcoming"]:
        params["eventType"] = event_type

    res = requests.get(url, params=params)
    if res.status_code == 403:
        print(f"⚠️ 403 Forbidden for channel {channel_id} ({event_type})")
        return []
    res.raise_for_status()

    items = res.json().get("items", [])
    return [item["id"]["videoId"] for item in items if "id" in item]


def fetch_details(video_ids):
    """videoIdリストから詳細情報をまとめて取得"""
    if not video_ids:
        return []
    url = "https://www.googleapis.com/youtube/v3/videos"
    params = {
        "part": "snippet,liveStreamingDetails",
        "id": ",".join(video_ids),
        "key": API_KEY,
    }
    res = requests.get(url, params=params)
    if res.status_code == 403:
        print("⚠️ 403 Forbidden during details fetch")
        return []
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
    """全チャンネルの配信データを分類して収集"""
    data = {"live": [], "upcoming": [], "completed": []}
    for cid in CHANNEL_IDS:
        for etype in ["live", "upcoming", "completed"]:
            vids = fetch_videos(cid, etype)
            details = fetch_details(vids)
            for v in details:
                # completed判定補強（liveBroadcastContentがnoneならアーカイブ扱い）
                if etype == "completed" and v["status"] == "none":
                    v["status"] = "completed"
                data[v["status"]].append(v)

    # ⏰ 各カテゴリを時刻順にソート
    for key in data:
        data[key].sort(key=lambda x: x.get("scheduled", "") or "9999-99-99T99:99:99Z")

    return data


if __name__ == "__main__":
    print("🚀 Fetching YouTube stream data...")
    data = collect_all()

    # 出力ディレクトリ作成
    os.makedirs("data", exist_ok=True)
    with open("data/streams.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("✅ streams.json updated successfully!")
