import os
import json
import requests
from datetime import datetime

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
BACKUP_PATH = "data/streams_backup.json"

# ==============================================================
# 📦 Utility
# ==============================================================

def load_cache():
    """前回の streams.json を読み込む（なければ空データ）"""
    if not os.path.exists(DATA_PATH):
        return {"live": [], "upcoming": [], "completed": [], "uploaded": [], "shorts": [], "freechat": []}
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            if not any(data.values()):
                print("⚠️ Cache file is empty, ignoring cache.")
                return {"live": [], "upcoming": [], "completed": [], "uploaded": [], "shorts": [], "freechat": []}
            return data
        except json.JSONDecodeError:
            print("⚠️ Invalid JSON in cache, starting fresh.")
            return {"live": [], "upcoming": [], "completed": [], "uploaded": [], "shorts": [], "freechat": []}

def backup_current():
    """現在のJSONをバックアップ"""
    if os.path.exists(DATA_PATH):
        os.makedirs("data", exist_ok=True)
        with open(DATA_PATH, "r", encoding="utf-8") as src, open(BACKUP_PATH, "w", encoding="utf-8") as dst:
            dst.write(src.read())
        print("🗂️  Backup created:", BACKUP_PATH)

# ==============================================================
# 📡 API calls
# ==============================================================

def fetch_videos(channel_id, event_type):
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "channelId": channel_id,
        "type": "video",
        "maxResults": 30,
        "order": "date",
        "key": API_KEY,
    }
    if event_type in ["live", "upcoming"]:
        params["eventType"] = event_type

    res = requests.get(url, params=params)
    if res.status_code == 403:
        print(f"⚠️ 403 Forbidden for {channel_id} ({event_type})")
        return []
    res.raise_for_status()
    items = res.json().get("items", [])
    return [item["id"]["videoId"] for item in items if "id" in item]

def fetch_details(video_ids):
    """動画詳細を取得し、分類を含めて返す"""
    if not video_ids:
        return []
    url = "https://www.googleapis.com/youtube/v3/videos"
    params = {
        "part": "snippet,contentDetails,liveStreamingDetails",
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
        content = item.get("contentDetails", {})

        # === 動画分類 ===
        if snippet.get("liveBroadcastContent") in ["live", "upcoming"]:
            status = snippet["liveBroadcastContent"]
        elif live.get("actualStartTime") and live.get("actualEndTime"):
            status = "completed"
        elif "shorts" in item["id"] or "shorts" in snippet.get("title", "").lower() or "shorts" in snippet.get("description", "").lower():
            status = "shorts"
        else:
            status = "uploaded"

        videos.append({
            "id": item["id"],
            "title": snippet.get("title", ""),
            "channel": snippet.get("channelTitle", ""),
            "channel_id": snippet.get("channelId", ""),
            "description": snippet.get("description", ""),
            "thumbnail": snippet.get("thumbnails", {}).get("high", {}).get("url", ""),
            "url": f"https://www.youtube.com/watch?v={item['id']}",
            "scheduled": live.get("scheduledStartTime", ""),
            "status": status
        })
    return videos

# ==============================================================
# ⚙️ Main logic
# ==============================================================

def collect_all():
    cache = load_cache()
    new_data = {"live": [], "upcoming": [], "completed": [], "uploaded": [], "shorts": [], "freechat": []}

    for cid in CHANNEL_IDS:
        print(f"🔍 Checking channel {cid} ...")
        cached_videos = sum([[v for v in cache[k] if cid in v.get("url", "")] for k in cache], [])
        cached_ids = {v["id"] for v in cached_videos}

        updated = False
        for etype in ["live", "upcoming", "completed"]:
            vids = fetch_videos(cid, etype)
            if not vids:
                continue
            new_ids = set(vids) - cached_ids
            if new_ids:
                updated = True
                details = fetch_details(list(new_ids))
                for v in details:
                    if "フリーチャット" in v["title"] or "フリースペース" in v["title"]:
                        new_data["freechat"].append(v)
                    else:
                        new_data[v["status"]].append(v)

        if not updated:
            print(f"  ✅ No update for {cid}, using cache")
            for k in cache:
                new_data[k].extend([v for v in cache[k] if v["id"] in cached_ids])

    for key in new_data:
        new_data[key].sort(key=lambda x: x.get("scheduled", "") or "9999-99-99T99:99:99Z")

    return new_data

# ==============================================================
# 🚀 Run
# ==============================================================

if __name__ == "__main__":
    print("🚀 Fetching YouTube stream data with safety + cache...")
    backup_current()
    data = collect_all()

    if not any(data.values()):
        print("🛑 All categories empty, keeping old data.")
    else:
        os.makedirs("data", exist_ok=True)
        with open(DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✅ streams.json updated at {datetime.now().isoformat()}")

    print("🏁 Done.")
