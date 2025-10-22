// ==========================
// 🎬 YouTube配信スケジュール表示
// そちまる公式風カスタム版（LIVE中強調）
// ==========================

const CHANNEL_MAP = {
  "UCgbQLx3kC5_i-0J_empIsxA": { name: "紅麗もあ", icon: "./assets/icons/more.jpg" },
  "UCSxorXiovSSaafcDp_JJAjg": { name: "矢筒あぽろ", icon: "./assets/icons/apollo.jpg" },
  "UCyBaf1pv1dO_GnkFBg1twLA": { name: "魔儘まほ", icon: "./assets/icons/maho.jpg" },
  "UCsy_jJ1qOyhr7wA4iKiq4Iw": { name: "戯びび", icon: "./assets/icons/bibi.jpg" },
  "UCrw103c53EKupQnNQGC4Gyw": { name: "乙眠らむ", icon: "./assets/icons/ramu.jpg" },
  "UC_kfGHWj4_7wbG3dBLnscRA": { name: "雷鎚ぴこ", icon: "./assets/icons/pico.jpg" },
  "UCPFrZbMFbZ47YO7OBnte_-Q": { name: "そちまる公式", icon: "./assets/icons/sochimaru.jpg" }
};

document.addEventListener("DOMContentLoaded", async () => {
  const data = await fetch("./data/streams.json").then(res => res.json());
  const categories = ["live", "upcoming", "completed", "uploaded", "freechat"];
  let currentChannel = "all";

  // ===== チャンネル選択メニュー =====
  const selectBtn = document.getElementById("currentChannel");
  const selectMenu = document.getElementById("channelMenu");

  function buildChannelMenu() {
    selectMenu.innerHTML = "";
    const allItem = document.createElement("div");
    allItem.className = "select-item";
    allItem.innerHTML = `<img src="./assets/icons/li.jpeg"><span>全チャンネル</span>`;
    allItem.addEventListener("click", () => selectChannel("all", "全チャンネル", "./assets/icons/li.jpeg"));
    selectMenu.appendChild(allItem);

    Object.entries(CHANNEL_MAP).forEach(([id, ch]) => {
      const item = document.createElement("div");
      item.className = "select-item";
      item.innerHTML = `<img src="${ch.icon}"><span>${ch.name}</span>`;
      item.addEventListener("click", () => selectChannel(id, ch.name, ch.icon));
      selectMenu.appendChild(item);
    });
  }

  function selectChannel(id, name, icon) {
    currentChannel = id;
    selectBtn.querySelector("img").src = icon;
    selectBtn.querySelector("span").textContent = name;
    selectMenu.classList.remove("open");
    renderAll();
  }

  selectBtn.addEventListener("click", () => selectMenu.classList.toggle("open"));
  document.addEventListener("click", e => {
    if (!e.target.closest(".custom-select")) selectMenu.classList.remove("open");
  });
  buildChannelMenu();

  // ===== タブ切り替え =====
  const tabs = document.querySelectorAll(".tab-btn");
  const sections = document.querySelectorAll(".tab-content");
  tabs.forEach(tab => {
    tab.addEventListener("click", () => {
      const target = tab.dataset.target;
      tabs.forEach(t => t.classList.remove("active"));
      tab.classList.add("active");
      sections.forEach(sec => sec.classList.toggle("active", sec.id === target));
    });
  });

  // ===== フリーチャット抽出 =====
  data.freechat = [];
  ["live", "upcoming", "completed", "uploaded"].forEach(cat => {
    data[cat] = (data[cat] || []).filter(v => {
      if (/フリーチャットスペース|フリースペース/.test(v.title)) {
        data.freechat.push(v);
        return false;
      }
      return true;
    });
  });

  // ==========================
  // 🧠 描画関数
  // ==========================
  function renderAll() {
    categories.forEach(key => {
      const container =
        document.getElementById(key) ||
        (key === "upcoming" ? document.getElementById("live") : null);

      if (!container) return;
      container.innerHTML = "";

      let list = data[key] || [];
      const filtered = currentChannel === "all" ? list : list.filter(v => v.channel_id === currentChannel);

      // === LIVE配信を最上部に固定 ===
      if (key === "live") {
        filtered.sort((a, b) => {
          if (a.status === "live" && b.status !== "live") return -1;
          if (a.status !== "live" && b.status === "live") return 1;
          return (a.scheduled < b.scheduled ? 1 : -1);
        });
      } else {
        filtered.sort((a, b) => (a.scheduled < b.scheduled ? 1 : -1));
      }

      // === 日付ごとにグループ化 ===
      const groups = {};
      filtered.forEach(v => {
        const d = v.scheduled ? new Date(v.scheduled) : new Date(v.published || Date.now());
        const year = d.getFullYear();
        const month = String(d.getMonth() + 1).padStart(2, "0");
        const day = String(d.getDate()).padStart(2, "0");
        const keyDate = `${year}-${month}-${day}`;
        if (!groups[keyDate]) groups[keyDate] = [];
        groups[keyDate].push(v);
      });

      // === 表示 ===
      Object.keys(groups)
        .sort((a, b) => (a < b ? 1 : -1))
        .forEach(dayKey => {
          const [_, m, d] = dayKey.split("-");

          // --- LIVE中配信だけ特別区切り表示 ---
          if (key === "live" && groups[dayKey].some(v => v.status === "live")) {
            const liveHeader = document.createElement("div");
            liveHeader.className = "date-divider live-divider";
            liveHeader.textContent = "—— LIVE中配信 ——";
            container.appendChild(liveHeader);
          }

          // --- 日付区切りをすべてのタブで表示 ---
          const dateHeader = document.createElement("div");
          dateHeader.className = "date-divider";
          dateHeader.textContent = `----- ${m}/${d} -----`;
          container.appendChild(dateHeader);

          groups[dayKey].forEach(v => {
            const vid = (v.channel_id || v.channelId || "").trim();
            const ch = CHANNEL_MAP[vid] || { name: v.channel, icon: "./assets/icons/li.jpeg" };
            const time = v.scheduled
              ? new Date(v.scheduled).toLocaleTimeString("ja-JP", { hour: "2-digit", minute: "2-digit" })
              : "--:--";
            const thumb = v.thumbnail
              ? v.thumbnail.replace(/mqdefault(_live)?/, "maxresdefault")
              : "./assets/icons/default-thumb.jpg";

            const showTime = !["uploaded", "freechat"].includes(key);
            const timeHTML = showTime ? `<div class="time">${time}</div>` : "";

            const card = document.createElement("div");
            card.className = "stream-row";
            if (v.status === "live") card.classList.add("onair");

            card.innerHTML = `
              <div class="left">
                ${timeHTML}
                <img src="${ch.icon}" class="ch-icon" alt="${ch.name}">
                <div class="ch-name">${ch.name}</div>
              </div>
              <div class="center">
                <h3 class="title" title="${v.title}">${v.title}</h3>
              </div>
              <div class="right">
                ${v.status === "live" ? '<span class="onair-badge">ON AIR</span>' : ""}
                <img src="${thumb}" class="thumb"
                     onerror="this.src=this.src.replace('maxresdefault','hqdefault')"
                     alt="${v.title}">
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
  }

  renderAll();
});

// ==========================
// 📺 モーダル
// ==========================
function openModal(v) {
  const modal = document.getElementById("modal");
  const body = document.getElementById("modal-body");
  const thumb = v.thumbnail
    ? v.thumbnail.replace(/mqdefault(_live)?/, "maxresdefault")
    : "./assets/icons/default-thumb.jpg";
  const scheduled = v.scheduled
    ? new Date(v.scheduled).toLocaleString("ja-JP", {
        year: "numeric", month: "long", day: "numeric",
        hour: "2-digit", minute: "2-digit"
      })
    : "日時未定";

  body.innerHTML = `
    <img src="${thumb}" style="width:100%; border-radius:6px; margin-bottom:10px;"
         onerror="this.src=this.src.replace('maxresdefault','hqdefault')">
    <h2>${v.title}</h2>
    <p style="color:#c88bff; font-weight:600;">${v.channel}</p>
    <p style="font-size:13px; color:#999;">${scheduled}</p>
    <p style="white-space: pre-wrap; line-height:1.6; margin-top:12px;">${v.description || "説明なし"}</p>
    <div style="margin-top:16px; text-align:center;">
      <a href="${v.url}" target="_blank"
         style="background:#ff0000; color:white; padding:10px 20px; border-radius:6px;
         text-decoration:none; font-weight:600;">YouTubeで視聴</a>
    </div>
  `;

  modal.style.display = "flex";
  modal.addEventListener("click", e => {
    if (e.target.classList.contains("modal") || e.target.classList.contains("modal-close")) {
      modal.style.display = "none";
    }
  });
}
