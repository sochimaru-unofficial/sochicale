import os
import json
import requests

API_KEY = os.environ["YOUTUBE_API_KEY"]

CHANNEL_IDS = [
    "UCgbQLx3kC5_i-0J_empIsxA",
    "UCSxorXiovSSaafcDp_JJAjg",
    "UCyBaf1pv1dO_GnkFBg1twLA",
    "UCsy_jJ1qOyhr7wA4iKiq4Iw",
    "UCrw103c53EKupQnNQGC4Gyw",
    "UC_kfGHWj4_7wbG3dBLnscRA",
    "UCPFrZbMFbZ47YO7OBnte_-Q",
]

DATA_PATH = "data/streams.json"

def load_cache():
    """前回のstreams.jsonを読み込む"""
    if not os.path.exists(DATA_PATH):
        return {"live": [], "upcoming": [], "completed": []}
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

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
    """全チャンネルの配信データを分類して収集（キャッシュ対応）"""
    cache = load_cache()
    new_data = {"live": [], "upcoming": [], "completed": []}

    for cid in CHANNEL_IDS:
        print(f"🔍 Checking channel {cid} ...")
        channel_cache = sum(
            [[v for v in cache[k] if "channel" in v and cid in v.get("url", "")] for k in cache],
            []
        )

        # 🟢 直近の動画IDをキャッシュから取得
        cached_ids = {v["id"] for v in channel_cache}
        latest_ids = set()

        # 🟢 APIコールを最小化
        updated = False
        for etype in ["live", "upcoming", "completed"]:
            vids = fetch_videos(cid, etype)
            latest_ids |= set(vids)
            if not vids:
                continue
            if not cached_ids.issuperset(vids):
                print(f"  ↪ Detected new/changed videos for {etype}")
                updated = True
                details = fetch_details(vids)
                for v in details:
                    if etype == "completed" and v["status"] == "none":
                        v["status"] = "completed"
                    new_data[v["status"]].append(v)

        if not updated:
            # 🟢 キャッシュ再利用
            print(f"  ✅ No update for {cid}, using cached data")
            for k in cache:
                new_data[k].extend([v for v in cache[k] if v["id"] in cached_ids])

    # ⏰ 各カテゴリを時刻順にソート
    for key in new_data:
        new_data[key].sort(key=lambda x: x.get("scheduled", "") or "9999-99-99T99:99:99Z")

    return new_data


if __name__ == "__main__":
    print("🚀 Fetching YouTube stream data with cache...")
    data = collect_all()
    os.makedirs("data", exist_ok=True)
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("✅ streams.json updated (with cache)!")
