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
        return {"live": [], "upcoming": [], "completed": [], "freechat": [] }
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            for key in ["live", "upcoming", "completed", "freechat"]:
                if key not in data:
                    data[key] = []
            if not any(data.values()):  # 全部空ならキャッシュ無効
                print("⚠️ Cache file is empty, ignoring cache.")
                return {"live": [], "upcoming": [], "completed": [], "freechat": []}
            return data
        except json.JSONDecodeError:
            print("⚠️ Invalid JSON in cache, starting fresh.")
            return {"live": [], "upcoming": [], "completed": [], "freechat": []}

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
            "channel_id": snippet.get("channelId", ""),  
            "description": snippet.get("description", ""),
            "thumbnail": snippet.get("thumbnails", {}).get("medium", {}).get("url", ""),
            "url": f"https://www.youtube.com/watch?v={item['id']}",
            "scheduled": live.get("scheduledStartTime", ""),
            "status": snippet.get("liveBroadcastContent", "none")
        })
    return videos

# ==============================================================
# ⚙️ Main logic with cache + safety
# ==============================================================

def collect_all():
    cache = load_cache()
    new_data = {"live": [], "upcoming": [], "completed": [], "freechat": [] }

    for cid in CHANNEL_IDS:
        print(f"🔍 Checking channel {cid} ...")
        channel_cache = sum(
            [[v for v in cache[k] if cid in v.get("url", "")] for k in cache],
            []
        )

        cached_ids = {v["id"] for v in channel_cache}
        latest_ids = set()

        updated = False
        # ★ freechat は APIで取得しない（3カテゴリだけ）
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

        # ★ 更新なしならキャッシュを再利用
        if not updated:
            print(f"  ✅ No update for {cid}, using cache")
            for k in cache:
                new_data[k].extend([v for v in cache.get(k, []) if v["id"] in cached_ids])

    # ★ フリーチャットはタイトルから自動抽出
    for cat in ["live", "upcoming", "completed"]:
        for v in new_data[cat][:]:
            if any(word in v["title"] for word in ["フリーチャット", "フリースペース"]):
                new_data["freechat"].append(v)
                new_data[cat].remove(v)
    for key in new_data:
        new_data[key].sort(key=lambda x: x.get("scheduled", "") or "9999-99-99T99:99:99Z")

    return new_data

# ==============================================================
# 🚀 Run
# ==============================================================

if __name__ == "__main__":
    print("🚀 Fetching YouTube stream data with safety + cache...")

    # バックアップ作成
    backup_current()

    # 新データ収集
    data = collect_all()

    # ⚠️ 全カテゴリが空の場合 → 上書き中止
    if not any(data.values()):
        print("🛑 All categories are empty! Keeping old data.")
    else:
        os.makedirs("data", exist_ok=True)
        with open(DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✅ streams.json updated at {datetime.now().isoformat()}")

    print("🏁 Done.")


