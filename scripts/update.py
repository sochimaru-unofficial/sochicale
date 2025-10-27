import os
import re
import json
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
# 🧰 ユーティリティ
# ==========================================================
def load_cache():
    if not os.path.exists(DATA_PATH):
        return {"completed": [], "uploaded": [], "_meta": {}}
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        print("⚠️ JSON破損を検出。新規作成します。")
        return {"completed": [], "uploaded": [], "_meta": {}}


def backup_current():
    if os.path.exists(DATA_PATH):
        os.makedirs("data", exist_ok=True)
        with open(DATA_PATH, "r", encoding="utf-8") as src, open(BACKUP_PATH, "w", encoding="utf-8") as dst:
            dst.write(src.read())
        print(f"🗂️ バックアップ作成: {BACKUP_PATH}")


def save_data_safe(data):
    os.makedirs("data", exist_ok=True)
    tmp_path = DATA_PATH + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, DATA_PATH)
    print(f"💾 保存完了: {DATA_PATH}")


def merge_with_cache(old, new):
    merged = {k: [] for k in ["completed", "uploaded"]}
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


# ==========================================================
# 📡 YouTube API
# ==========================================================
def fetch_videos(channel_id, key, since=None, max_results=20):
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "channelId": channel_id,
        "type": "video",
        "order": "date",
        "maxResults": max_results,
        "key": key,
    }
    if since:
        params["publishedAfter"] = since

    try:
        res = requests.get(url, params=params)
        res.raise_for_status()
        return [i["id"]["videoId"] for i in res.json().get("items", []) if "id" in i]
    except Exception as e:
        print(f"❌ fetch_videos失敗: {channel_id} → {e}")
        return []


def classify_video_status(snippet, live, title):
    """YouTube動画の状態を分類（live / upcoming / completed / uploaded / freechat）"""

    status = snippet.get("liveBroadcastContent", "none")

    if "actualEndTime" in live:
        status = "completed"
    elif "actualStartTime" in live:
        status = "live"
    elif "scheduledStartTime" in live or status == "upcoming":
        status = "upcoming"

    # --- フリーチャット検出（多言語・全角半角対応）---
    title_lower = title.lower()
    freechat_pattern = re.compile(r"(フリ[ーｰ]チャット|フリ[ーｰ]スペース|free.?chat)", re.IGNORECASE)

    if freechat_pattern.search(title_lower):
        section = "freechat"
    elif status in ["live", "upcoming", "completed"]:
        section = status
    else:
        section = "uploaded"

    return status, section


def fetch_video_details(video_ids, key):
    """videos.listで詳細を取得"""
    if not video_ids:
        return []

    url = "https://www.googleapis.com/youtube/v3/videos"
    params = {
        "part": "snippet,liveStreamingDetails,contentDetails",
        "id": ",".join(video_ids),
        "key": key,
    }
    try:
        res = requests.get(url, params=params)
        res.raise_for_status()
        videos = []
        for item in res.json().get("items", []):
            snippet = item.get("snippet", {})
            live = item.get("liveStreamingDetails", {})
            title = snippet.get("title", "")

            status, section = classify_video_status(snippet, live, title)

            videos.append({
                "id": item["id"],
                "title": title,
                "channel": snippet.get("channelTitle", ""),
                "channel_id": snippet.get("channelId", ""),
                "description": snippet.get("description", ""),
                "thumbnail": snippet.get("thumbnails", {}).get("high", {}).get("url", ""),
                "url": f"https://www.youtube.com/watch?v={item['id']}",
                "scheduled": live.get("scheduledStartTime", ""),
                "published": snippet.get("publishedAt", ""),
                "status": status,
                "section": section,
            })
        return videos
    except Exception as e:
        print(f"❌ fetch_video_details失敗: {e}")
        return []


# ==========================================================
# 🧠 データ収集（Full専用）
# ==========================================================
def collect_all():
    cache = load_cache()
    new_data = {k: [] for k in ["completed", "uploaded"]}
    now = datetime.utcnow()

    for cid, key in CHANNEL_KEYS.items():
        if not key:
            print(f"⚠️ APIキー未設定: {cid}")
            continue

        print(f"🔍 チャンネル確認中: {cid}")
        since = CUTOFF.strftime("%Y-%m-%dT%H:%M:%SZ")

        video_ids = fetch_videos(cid, key, since=since, max_results=50)
        videos = fetch_video_details(video_ids, key)

        for v in videos:
            if v["section"] == "completed":
                new_data["completed"].append(v)
            else:
                new_data["uploaded"].append(v)

        cache["_meta"][cid] = now.isoformat()

    # --- 古いデータ整理 ---
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=DAYS_LIMIT)
    for section in ["completed", "uploaded"]:
        new_data[section] = [
            v for v in new_data[section]
            if v.get("published") and datetime.fromisoformat(v["published"].replace("Z", "+00:00")) > cutoff_date
        ]

    return new_data


# ==========================================================
# 🚀 メイン実行
# ==========================================================
if __name__ == "__main__":
    print("🚀 実行モード: FULL（リアルタイム部分はWorkerに移行）")
    backup_current()
    old_data = load_cache()

    try:
        new_data = collect_all()
        merged = merge_with_cache(old_data, new_data)
        save_data_safe(merged)
        print("✅ 更新完了！")
    except Exception as e:
        print(f"❌ 更新エラー: {e}")
        save_data_safe(old_data)
