import os
import json
import requests
from datetime import datetime, timedelta, timezone

# ============================================================== #
# 🧩 設定
# ============================================================== #

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

DAYS_LIMIT = 30
CUTOFF = datetime.now(timezone.utc) - timedelta(days=DAYS_LIMIT)

# ============================================================== #
# 🧰 ユーティリティ
# ============================================================== #

def load_cache():
    if not os.path.exists(DATA_PATH):
        return {"live": [], "upcoming": [], "completed": [], "uploaded": [], "freechat": []}
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {"live": [], "upcoming": [], "completed": [], "uploaded": [], "freechat": []}

def backup_current():
    if os.path.exists(DATA_PATH):
        os.makedirs("data", exist_ok=True)
        with open(DATA_PATH, "r", encoding="utf-8") as src, open(BACKUP_PATH, "w", encoding="utf-8") as dst:
            dst.write(src.read())
        print(f"🗂️ Backup created: {BACKUP_PATH}")

# ============================================================== #
# 🎬 詳細情報取得
# ============================================================== #

def fetch_details(video_ids, key):
    if not video_ids:
        return []

    url = "https://www.googleapis.com/youtube/v3/videos"
    params = {
        "part": "snippet,liveStreamingDetails,contentDetails",
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

        title = snippet.get("title", "")
        published = snippet.get("publishedAt", "")
        scheduled = live.get("scheduledStartTime", "")
        status = snippet.get("liveBroadcastContent", "none")

        # --- liveStreamingDetails を使って実際の配信状態を再評価 ---
        if "actualEndTime" in live:
            status = "completed"
        elif "actualStartTime" in live:
            status = "live"
        elif "scheduledStartTime" in live:
            status = "upcoming"
        
        # === セクション分類（statusに合わせて） ===
        if "フリーチャット" in title or "フリースペース" in title:
            section = "freechat"
        elif status == "live":
            section = "live"
        elif status == "upcoming":
            section = "upcoming"
        elif status == "completed":
            section = "completed"
        else:
            section = "uploaded"


        # === セクション分類 ===
        if "フリーチャット" in title or "フリースペース" in title:
            section = "freechat"
        elif status == "live":
            section = "live"
        elif status == "upcoming":
            section = "upcoming"
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
            "thumbnail": snippet.get("thumbnails", {}).get("high", {}).get("url", ""),
            "url": f"https://www.youtube.com/watch?v={item['id']}",
            "scheduled": scheduled,
            "published": published,
            "status": status,
            "section": section,
        })
    return videos

# ============================================================== #
# 🔄 メイン収集
# ============================================================== #

def fetch_videos(channel_id, event_type=None, key=None):
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
        res = requests.get(url, params=params)
        if res.status_code == 403:
            print(f"⚠️ 403 Forbidden for {channel_id} ({event_type})")
            return []
        res.raise_for_status()
        data = res.json()

        # 🧩 Fallback: 突発ライブ対応（liveで0件なら通常検索へ）
        if not data.get("items"):
            print(f"⚠️ {channel_id}: no {event_type} items, fallback to normal search")
            del params["eventType"]
            res = requests.get(url, params=params)
            res.raise_for_status()
            data = res.json()

        return [item["id"]["videoId"] for item in data.get("items", []) if "id" in item]

    else:
        params["publishedAfter"] = CUTOFF.strftime("%Y-%m-%dT%H:%M:%SZ")
        res = requests.get(url, params=params)
        if res.status_code == 403:
            print(f"⚠️ 403 Forbidden for {channel_id} (normal)")
            return []
        res.raise_for_status()
        return [item["id"]["videoId"] for item in res.json().get("items", []) if "id" in item]


def collect_all():
    cache = load_cache()
    new_data = {"live": [], "upcoming": [], "completed": [], "uploaded": [], "freechat": []}

    for cid, key in CHANNEL_KEYS.items():
        if not key:
            print(f"⚠️ Missing API key for {cid}, skipping.")
            continue

        print(f"🔍 Checking channel {cid} ...")

        # --- upcoming ---
        upcoming_ids = fetch_videos(cid, "upcoming", key)
        upcoming = fetch_details(upcoming_ids, key)
        new_data["upcoming"].extend(upcoming)

        # --- live ---
        live_ids = fetch_videos(cid, "live", key)
        live = fetch_details(live_ids, key)
        new_data["live"].extend(live)

        # --- 通常動画（6時間おき） ---
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

    # --- 30日以上前を削除 ---
    for k in ["completed", "uploaded"]:
        new_data


