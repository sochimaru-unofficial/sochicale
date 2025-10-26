import os
import json
import sys
import requests
from datetime import datetime, timedelta, timezone

# ==========================================================
# ⚙️ 設定
# ==========================================================
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


# ==========================================================
# 🧰 基本ユーティリティ
# ==========================================================
def load_cache():
    if not os.path.exists(DATA_PATH):
        return {"live": [], "upcoming": [], "completed": [], "uploaded": [], "_meta": {}}
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        print("⚠️ Corrupted JSON detected. Starting fresh.")
        return {"live": [], "upcoming": [], "completed": [], "uploaded": [], "_meta": {}}


def backup_current():
    if os.path.exists(DATA_PATH):
        os.makedirs("data", exist_ok=True)
        with open(DATA_PATH, "r", encoding="utf-8") as src, open(BACKUP_PATH, "w", encoding="utf-8") as dst:
            dst.write(src.read())
        print(f"🗂️ Backup created: {BACKUP_PATH}")


def save_data_safe(data):
    os.makedirs("data", exist_ok=True)
    tmp_path = DATA_PATH + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, DATA_PATH)
    print(f"💾 Saved: {DATA_PATH}")


def merge_with_cache(old, new):
    merged = {k: [] for k in ["live", "upcoming", "completed", "uploaded"]}
    seen = set()

    for sec in merged:
        for v in old.get(sec, []):
            merged[sec].append(v)
            seen.add(v["id"])

    for sec in merged:
        for v in new.get(sec, []):
            if v["id"] not in seen:
                merged[sec].append(v)
                seen.add(v["id"])

    merged["_meta"] = old.get("_meta", {})
    return merged


def build_state_cache(old_data):
    state_cache = {}
    for section in ["live", "upcoming", "completed", "uploaded"]:
        for v in old_data.get(section, []):
            state_cache[v["id"]] = v.get("status", section)
    return state_cache


# ==========================================================
# 📡 YouTube API呼び出し
# ==========================================================
def fetch_videos(channel_id, event_type=None, key=None, since=None, max_results=20):
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "channelId": channel_id,
        "type": "video",
        "order": "date",
        "maxResults": max_results,
        "key": key,
    }
    if event_type in ["live", "upcoming"]:
        params["eventType"] = event_type
    else:
        params["publishedAfter"] = since or CUTOFF.strftime("%Y-%m-%dT%H:%M:%SZ")

    try:
        res = requests.get(url, params=params)
        if res.status_code == 403:
            print(f"⚠️ 403 Forbidden for {channel_id} ({event_type or 'video'})")
            return []
        res.raise_for_status()
        return [item["id"]["videoId"] for item in res.json().get("items", []) if "id" in item]
    except Exception as e:
        print(f"❌ Error fetching videos for {channel_id}: {e}")
        return []


def fetch_details_filtered(video_ids, key, state_cache, mode):
    if not video_ids:
        return []

    videos = []
    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i:i+50]
        url = "https://www.googleapis.com/youtube/v3/videos"
        params = {
            "part": "snippet,liveStreamingDetails,contentDetails",
            "id": ",".join(chunk),
            "key": key,
        }
        try:
            res = requests.get(url, params=params)
            res.raise_for_status()
            for item in res.json().get("items", []):
                snippet = item.get("snippet", {})
                live = item.get("liveStreamingDetails", {})
                title = snippet.get("title", "")
                status = snippet.get("liveBroadcastContent", "none")

                actual_start = live.get("actualStartTime")
                actual_end = live.get("actualEndTime")
                scheduled = live.get("scheduledStartTime")

                # ===== 💡 ステータス補正ロジック =====
                if actual_end:
                    status = "completed"
                elif actual_start:
                    start_dt = datetime.fromisoformat(actual_start.replace("Z", "+00:00"))
                    if datetime.now(timezone.utc) - start_dt > timedelta(hours=8):
                        status = "completed"  # 長時間経過で強制アーカイブ
                    else:
                        status = "live"
                elif scheduled:
                    status = "upcoming"
                else:
                    status = "uploaded"

                section = (
                    "freechat" if "フリーチャット" in title or "フリースペース" in title
                    else status if status in ["live", "upcoming", "completed"]
                    else "uploaded"
                )

                videos.append({
                    "id": item["id"],
                    "title": title,
                    "channel": snippet.get("channelTitle", ""),
                    "channel_id": snippet.get("channelId", ""),
                    "description": snippet.get("description", ""),
                    "thumbnail": snippet.get("thumbnails", {}).get("high", {}).get("url", ""),
                    "url": f"https://www.youtube.com/watch?v={item['id']}",
                    "scheduled": scheduled,
                    "published": snippet.get("publishedAt", ""),
                    "status": status,
                    "section": section,
                })
        except Exception as e:
            print(f"❌ Error fetching details: {e}")
    return videos


# ==========================================================
# 🧠 データ収集
# ==========================================================
def collect_all(mode="light"):
    cache = load_cache()
    state_cache = build_state_cache(cache)
    new_data = {"live": [], "upcoming": [], "completed": [], "uploaded": []}
    now = datetime.utcnow()

    for cid, key in CHANNEL_KEYS.items():
        if not key:
            print(f"⚠️ Missing API key for {cid}, skipping.")
            continue

        try:
            print(f"🔍 Checking channel: {cid}")
            last_iso = cache.get("_meta", {}).get(cid)
            since = last_iso or CUTOFF.strftime("%Y-%m-%dT%H:%M:%SZ")

            upcoming_ids = fetch_videos(cid, "upcoming", key)
            live_ids = fetch_videos(cid, "live", key)
            upcoming = fetch_details_filtered(upcoming_ids, key, state_cache, mode)
            live = fetch_details_filtered(live_ids, key, state_cache, mode)
            new_data["upcoming"].extend(upcoming)
            new_data["live"].extend(live)

            if mode == "full":
                uploaded_ids = fetch_videos(cid, None, key, since=CUTOFF.strftime("%Y-%m-%dT%H:%M:%SZ"), max_results=50)
            else:
                uploaded_ids = fetch_videos(cid, None, key, since=since, max_results=20)
            uploaded = fetch_details_filtered(uploaded_ids, key, state_cache, mode)
            new_data["uploaded"].extend(uploaded)

            cache["_meta"][cid] = now.isoformat()
        except Exception as e:
            print(f"❌ Channel {cid} failed: {e}")
            continue

    cutoff_date = datetime.now(timezone.utc) - timedelta(days=DAYS_LIMIT)
    for category in ["completed", "uploaded"]:
        new_data[category] = [
            v for v in new_data[category]
            if v.get("published") and datetime.fromisoformat(v["published"].replace("Z", "+00:00")) > cutoff_date
        ]

    return new_data


# ==========================================================
# 🚀 メイン実行
# ==========================================================
if __name__ == "__main__":
    mode = "light"
    if len(sys.argv) > 1 and sys.argv[1] == "--mode=full":
        mode = "full"

    print(f"🚀 Starting update in [{mode.upper()}] mode")
    backup_current()
    old_data = load_cache()

    try:
        new_data = collect_all(mode)
        if not new_data:
            print("⚠️ No data fetched. Keeping previous JSON.")
            sys.exit(0)

        merged = merge_with_cache(old_data, new_data)
        save_data_safe(merged)
        print("✅ Update complete.")
    except Exception as e:
        print(f"❌ Update failed: {e}")
        print("⏪ Restoring previous JSON.")
        save_data_safe(old_data)
