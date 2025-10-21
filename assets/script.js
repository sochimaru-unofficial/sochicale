// ===== チャンネルIDと表示名・アイコンの対応表 =====
const CHANNEL_MAP = {
  "UCgbQLx3kC5_i-0J_empIsxA": { name: "紅麗もあ", icon: "./assets/icons/more.jpg" },
  "UCSxorXiovSSaafcDp_JJAjg": { name: "矢筒あぽろ", icon: "./assets/icons/apollo.jpg" },
  "UCyBaf1pv1dO_GnkFBg1twLA": { name: "魔儘まほ", icon: "./assets/icons/maho.jpg" },
  "UCsy_jJ1qOyhr7wA4iKiq4Iw": { name: "戯びび", icon: "./assets/icons/bibi.jpg" },
  "UCrw103c53EKupQnNQGC4Gyw": { name: "乙眠らむ", icon: "./assets/icons/ramu.jpg" },
  "UC_kfGHWj4_7wbG3dBLnscRA": { name: "雷鎚ぴこ", icon: "./assets/icons/pico.jpg" },
  "UCPFrZbMFbZ47YO7OBnte_-Q": { name: "そちまる公式", icon: "./assets/icons/sochimaru.jpg" }
};

// ===== メイン処理 =====
document.addEventListener("DOMContentLoaded", async () => {
  const data = await fetch("./data/streams.json").then(res => res.json());
  const categories = ["live", "upcoming", "completed"];

  categories.forEach(key => {
    const container = document.getElementById(key);
    const list = data[key] || [];
    list.sort((a, b) => (a.scheduled < b.scheduled ? 1 : -1));

    // === 日付ごとにグループ化 ===
    const groups = {};
    list.forEach(v => {
      const d = v.scheduled
        ? new Date(v.scheduled)
        : new Date(v.published || Date.now());
      // 日付キーを「MM/DD」形式に
      const dayKey = `${String(d.getMonth() + 1).padStart(2, "0")}/${String(d.getDate()).padStart(2, "0")}`;
      if (!groups[dayKey]) groups[dayKey] = [];
      groups[dayKey].push(v);
    });

    // === 各日付ごとに描画 ===
    Object.keys(groups)
      .sort((a, b) => (a < b ? 1 : -1))
      .forEach(dayKey => {
        // 区切り線
        const dateHeader = document.createElement("div");
        dateHeader.className = "date-divider";
        dateHeader.textContent = `----- ${dayKey} -----`;
        container.appendChild(dateHeader);

        groups[dayKey].forEach(v => {
          const cid = v.channelId && CHANNEL_MAP[v.channelId] ? v.channelId : null;
          const ch = cid ? CHANNEL_MAP[cid] : { name: v.channel, icon: "./assets/icons/default.png" };

          const time = v.scheduled
            ? new Date(v.scheduled).toLocaleTimeString("ja-JP", {
                hour: "2-digit",
                minute: "2-digit",
              })
            : "--:--";

          const card = document.createElement("div");
          card.className = "stream-row";
          if (v.status === "live") card.classList.add("onair");

          // === カード構造 ===
          card.innerHTML = `
            <div class="left">
              <div class="time">${time}</div>
              <img src="${ch.icon}" class="ch-icon" alt="${ch.name}">
              <div class="ch-name">${ch.name}</div>
            </div>
            <div class="center">
              <h3 class="title" title="${v.title}">${v.title}</h3>
            </div>
            <div class="right">
              ${v.status === "live" ? '<span class="onair-badge">ON AIR</span>' : ""}
              <img src="${v.thumbnail}" class="thumb" alt="${v.title}">
            </div>
          `;

          card.addEventListener("click", e => {
            e.stopPropagation();
            openModal(v);
          });

          container.appendChild(card);
        });
      });
  });
});

// ===== モーダル表示 =====
function openModal(v) {
  const modal = document.getElementById("modal");
  const body = document.getElementById("modal-body");

  const scheduled = v.scheduled
    ? new Date(v.scheduled).toLocaleString("ja-JP", {
        month: "long",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      })
    : "日時未定";

  body.innerHTML = `
    <img src="${v.thumbnail}" style="width:100%; border-radius:6px; margin-bottom:10px;">
    <h2>${v.title}</h2>
    <p style="color:#0070f3; font-weight:600;">${v.channel}</p>
    <p style="font-size:13px; color:#666;">${scheduled}</p>
    <p style="white-space: pre-wrap; line-height:1.6; margin-top:12px;">
      ${v.description || "説明なし"}
    </p>
    <div style="margin-top:16px; text-align:center;">
      <a href="${v.url}" target="_blank" style="
        background:#ff0000;
        color:white;
        padding:10px 20px;
        border-radius:6px;
        text-decoration:none;
        font-weight:600;
      ">YouTubeで視聴</a>
    </div>
  `;

  modal.style.display = "flex";
  modal.addEventListener("click", e => {
    if (e.target.classList.contains("modal") || e.target.classList.contains("modal-close")) {
      modal.style.display = "none";
    }
  });
}
