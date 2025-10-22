import os
import json
import requests
from datetime import datetime, timedelta

# ==============================================================
# 🧩 設定
# ==============================================================

CHANNEL_KEYS = {
    "UCgbQLx3kC5_i-0J_empIsxA": os.environ.get("YOUTUBE_KEY_MORE"),
    "UCSxorXiovSSaafcDp_JJAjg": os.environ.get("YOUTUBE_KEY_APOLLO"),
    "UCyBaf1pv1dO_GnkFBg1twLA": os.environ.get("YOUTUBE_KEY_MAHO"),
    "UCsy_jJ1qOyhr7wA4iKiq4Iw": os.environ.get("YOUTUBE_KEY_BIBI"),
    "UCrw103c53EKupQnNQGC4Gyw": os.environ.get("YOUTUBE_KEY_RAMU"),
    "UC_kfGHWj4_7wbG3dBLnscRA": os.environ.get("YOUTUBE_KEY_PICO"),
    "UCPFrZbMFbZ47YO7OBnte_-Q": os.environ.get("YOUTUBE_KEY_SOCHIMARU"),
}

DATA_PATH = "data/streams.json"
BACKUP_PATH = "data/streams_backup.json"

DAYS_LIMIT = 30  # ← 30日制限
CUTOFF = datetime.utcnow() - timedelta(days=DAYS_LIMIT)

# ==============================================================
# 🧰 ユーティリティ
# ==============================================================

def load_cache():
    """既存キャッシュを読み込み"""
    if not os.path.exists(DATA_PATH):
        return {"live": [], "upcoming": [], "completed": [], "uploaded": [], "shorts": [], "freechat": []}
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {"live": [], "upcoming": [], "completed": [], "uploaded": [], "shorts": [], "freechat": []}

def backup_current():
    """streams.json をバックアップ"""
    if os.path.exists(DATA_PATH):
        os.makedirs("data", exist_ok=True)
        with open(DATA_PATH, "r", encoding="utf-8") as src, open(BACKUP_PATH, "w", encoding="utf-8") as dst:
            dst.write(src.read())
        print(f"🗂️ Backup created: {BACKUP_PATH}")

def fetch_videos(channel_id, event_type=None, key=None):
    """YouTube search API 呼び出し"""
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "channelId": channel_id,
        "type": "video",
        "order": "date",
        "maxResults": 50,
        "key": key,
    }
    if event_type in ["live", "upcoming"]:
        params["eventType"] = event_type
    else:
        # 通常動画・shortsなどは30日制限を付与
        params["publishedAfter"] = CUTOFF.isoformat("T") + "Z"

    res = requests.get(url, params=params)
    if res.status_code == 403:
        print(f"⚠️ 403 Forbidden for {channel_id} ({event_type or 'video'})")
        return []
    res.raise_for_status()
    return [item["id"]["videoId"] for item in res.json().get("items", []) if "id" in item]

def fetch_details(video_ids, key):
    """動画の詳細情報を取得"""
    if not video_ids:
        return []
    url = "https://www.googleapis.com/youtube/v3/videos"
    params = {
        "part": "snippet,liveStreamingDetails",
        "id": ",".join(video_ids),
        "key": key,
    }
    res = requests.get(url, params=params)
    if res.status_code == 403:
        print("⚠️ 403 Forbidden during details fetch")
        return []
    res.raise_for_status()

    videos = []
    for item in res.json().get("items", []):
        snippet = item.get("snippet", {})
        live = item.get("liveStreamingDetails", {})
        published = snippet.get("publishedAt", "")
        scheduled = live.get("scheduledStartTime", "")
        status = snippet.get("liveBroadcastContent", "none")

        # フリーチャット判定
        title = snippet.get("title", "")
        if "フリーチャット" in title or "フリースペース" in title:
            section = "freechat"
        elif status == "live":
            section = "live"
        elif status == "upcoming":
            section = "upcoming"
        elif "shorts" in title.lower() or "ショート" in title:
            section = "shorts"
        elif scheduled or live.get("actualEndTime"):
            section = "completed"
        else:
            section = "uploaded"

        videos.append({
            "id": item["id"],
            "title": title,
            "channel": snippet.get("channelTitle", ""),
            "channel_id": snippet.get("channelId", ""),
            "description": snippet.get("description", ""),
            "thumbnail": snippet.get("thumbnails", {}).get("medium", {}).get("url", ""),
            "url": f"https://www.youtube.com/watch?v={item['id']}",
            "scheduled": scheduled,
            "published": published,
            "status": status,
            "section": section,
        })
    return videos

# ==============================================================
# 🔄 データ収集ロジック
# ==============================================================

def collect_all():
    cache = load_cache()
    new_data = {"live": [], "upcoming": [], "completed": [], "uploaded": [], "shorts": [], "freechat": []}

    for cid, key in CHANNEL_KEYS.items():
        if not key:
            print(f"⚠️ Missing API key for {cid}, skipping.")
            continue

        print(f"🔍 Checking channel {cid} ...")

        # --- upcomingを取得 ---
        upcoming_ids = fetch_videos(cid, "upcoming", key)
        upcoming = fetch_details(upcoming_ids, key)
        new_data["upcoming"].extend(upcoming)

        # --- liveを取得（upcomingが存在する or キャッシュにliveがある時だけ） ---
        has_live = any(v for v in cache.get("live", []) if v.get("channel_id") == cid)
        if upcoming_ids or has_live:
            live_ids = fetch_videos(cid, "live", key)
            live = fetch_details(live_ids, key)
            new_data["live"].extend(live)
        else:
            print(f"🕓 No active live for {cid}, skipping live fetch.")

        # --- 通常動画 / shorts を低頻度（キャッシュ判定付き） ---
        now = datetime.utcnow()
        last_update = cache.get("_meta", {}).get(cid)
        if not last_update or (now - datetime.fromisoformat(last_update)) > timedelta(hours=6):
            vid_ids = fetch_videos(cid, None, key)
            vids = fetch_details(vid_ids, key)
            for v in vids:
                if v["section"] in new_data:
                    new_data[v["section"]].append(v)
            cache["_meta"] = cache.get("_meta", {})
            cache["_meta"][cid] = now.isoformat()

        # --- live → completed への自動移行 ---
        for v in cache.get("live", []):
            if v.get("channel_id") == cid and v.get("status") == "none":
                v["section"] = "completed"
                new_data["completed"].append(v)

    # --- 30日以上前のデータは削除 ---
    for k in ["completed", "uploaded", "shorts"]:
        new_data[k] = [
            v for v in new_data[k]
            if v.get("published") and datetime.fromisoformat(v["published"].replace("Z", "+00:00")) > CUTOFF
        ]

    return new_data

# ==============================================================
# 🚀 実行
# ==============================================================

if __name__ == "__main__":
    print("🚀 Fetching YouTube stream data with smart caching and 30-day window...")
    backup_current()
    data = collect_all()

    if not any(data.values()):
        print("🛑 No valid data fetched. Keeping old JSON.")
    else:
        os.makedirs("data", exist_ok=True)
        with open(DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✅ streams.json updated ({datetime.now().isoformat()})")

    print("🏁 Done.")
