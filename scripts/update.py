import os
import json
import requests
from datetime import datetime, timedelta, timezone

# ==========================================================
# ⚙️ 設定
# ==========================================================
API_KEY = os.environ.get("CAL_UPDATE")

CHANNEL_KEYS = {
    "UCgbQLx3kC5_i-0J_empIsxA": API_KEY,  # 紅麗もあ🔥⚔️
    "UCSxorXiovSSaafcDp_JJAjg": API_KEY,  # 矢筒あぽろ🍃🏹
    "UCyBaf1pv1dO_GnkFBg1twLA": API_KEY,  # 魔儘まほ💧🪄
    "UCsy_jJ1qOyhr7wA4iKiq4Iw": API_KEY,  # 戯びび🎰🪙
    "UCrw103c53EKupQnNQGC4Gyw": API_KEY,  # 乙眠らむ🐏❤️‍🩹
    "UC_kfGHWj4_7wbG3dBLnscRA": API_KEY,  # 雷鎚ぴこ⚡🔨
    "UCPFrZbMFbZ47YO7OBnte_-Q": API_KEY,  # そちまる公式🪄✨
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
    """最新動画一覧を取得（予約枠・フリチャは除外）"""
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
        items = res.json().get("items", [])
        # 🔍 upcoming / フリチャ動画を除外
        return [
            i["id"]["videoId"]
            for i in items
            if "id" in i and i["snippet"]["liveBroadcastContent"] == "none"
        ]
    except Exception as e:
        print(f"❌ fetch_videos失敗: {channel_id} → {e}")
        return []


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
            status = "completed" if "actualEndTime" in live else "uploaded"

            # 🔍 ここでも保険として「フリチャ」「upcoming」弾く
            if snippet.get("liveBroadcastContent") != "none":
                continue
            if any(x in title for x in ["フリーチャット", "フリースペース", "Free Chat", "freechat", "free chat"]):
                continue

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
                "section": status,
            })
        return videos
    except Exception as e:
        print(f"❌ fetch_video_details失敗: {e}")
        return []


# ==========================================================
# 🧠 データ収集（履歴専用）
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
            if v["status"] == "completed":
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
    print("🚀 実行モード: FULL（リアルタイム部分はWorkerに移行済み）")
    backup_current()
    old_data = load_cache()

    try:
        new_data = collect_all()
        merged = merge_with_cache(old_data, new_data)
        save_data_safe(merged)
        print("✅ 更新完了！（upcoming / freechat 除外済み）")
    except Exception as e:
        print(f"❌ 更新エラー: {e}")
        save_data_safe(old_data)

