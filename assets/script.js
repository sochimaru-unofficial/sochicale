// ==========================
// 🎬 そちまる配信スケジュール（最終安定版）
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
  // 🔧 assets配下からのfetchに修正
  let data;
  try {
    data = await fetch("../data/streams.json").then(res => res.json());
  } catch (err) {
    console.error("streams.json取得エラー:", err);
    return;
  }

  // フリーチャット抽出（元仕様踏襲）
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

  let currentChannel = "all";

  // ===== チャンネル選択 =====
  const selectBtn = document.getElementById("currentChannel");
  const selectMenu = document.getElementById("channelMenu");

  function buildChannelMenu() {
    selectMenu.innerHTML = "";
    const addItem = (id, name, icon) => {
      const item = document.createElement("div");
      item.className = "select-item";
      item.innerHTML = `<img src="${icon}" alt="${name}"><span>${name}</span>`;
      item.addEventListener("click", () => selectChannel(id, name, icon));
      selectMenu.appendChild(item);
    };
    addItem("all", "全チャンネル", "./assets/icons/li.jpeg");
    Object.entries(CHANNEL_MAP).forEach(([id, ch]) => addItem(id, ch.name, ch.icon));
  }

  function selectChannel(id, name, icon) {
    currentChannel = id;
    selectBtn.querySelector("img").src = icon;
    selectBtn.querySelector("span").textContent = name;
    selectMenu.classList.remove("open");
    renderAll();
  }

  selectBtn.addEventListener("click", () => {
    selectMenu.classList.toggle("open");
    selectBtn.setAttribute("aria-expanded", selectMenu.classList.contains("open") ? "true" : "false");
  });
  document.addEventListener("click", (e) => {
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

  // ===== 描画 =====
  function renderAll() {
    const liveEl = document.getElementById("live");
    const completedEl = document.getElementById("completed");
    const uploadedEl = document.getElementById("uploaded");
    const freechatEl = document.getElementById("freechat");

    // live: live + upcoming（日時でグルーピング & 見出し）
    const liveList = filterByChannel((data.live || []).concat(data.upcoming || []));
    renderCategory(liveEl, liveList, "live");

    renderCategory(completedEl, filterByChannel(data.completed || []), "completed");
    renderCategory(uploadedEl, filterByChannel(data.uploaded || []), "uploaded");
    renderCategory(freechatEl, filterByChannel(data.freechat || []), "freechat");
  }

  function filterByChannel(list) {
    return currentChannel === "all" ? list : list.filter(v => v.channel_id === currentChannel);
  }

  function renderCategory(container, list, key) {
    container.innerHTML = "";
    if (!list.length) {
      container.innerHTML = `<p class="empty">該当する配信はありません。</p>`;
      return;
    }

    // liveカテゴリは「配信中」「配信予定」の見出しを分ける
    if (key === "live") {
      const liveNow = list.filter(v => v.section === "live");
      const upcoming = list.filter(v => v.section === "upcoming");

      if (liveNow.length) {
        container.appendChild(makeDivider("—— 配信中 ——"));
        renderByDate(container, liveNow, key);
      }
      if (upcoming.length) {
        container.appendChild(makeDivider("—— 配信予定 ——"));
        renderByDate(container, upcoming, key);
      }
      return;
    }

    // その他は日付グループで描画
    renderByDate(container, list, key);
  }

  function makeDivider(text) {
    const d = document.createElement("div");
    d.className = "date-divider";
    d.textContent = text;
    return d;
  }

  function renderByDate(container, videos, key) {
    const groups = {};
    videos.forEach(v => {
      const d = v.scheduled ? new Date(v.scheduled) : new Date(v.published || Date.now());
      const y = d.getFullYear();
      const m = String(d.getMonth() + 1).padStart(2, "0");
      const day = String(d.getDate()).padStart(2, "0");
      const dateKey = `${y}-${m}-${day}`;
      if (!groups[dateKey]) groups[dateKey] = [];
      groups[dateKey].push(v);
    });

    Object.keys(groups).sort((a, b) => (a < b ? 1 : -1)).forEach(dateKey => {
      const [_, m, d] = dateKey.split("-");
      container.appendChild(makeDivider(`----- ${m}/${d} -----`));
      groups[dateKey].forEach(v => container.appendChild(createCard(v)));
    });
  }

  function createCard(v) {
    const ch = CHANNEL_MAP[v.channel_id] || { name: v.channel, icon: "./assets/icons/li.jpeg" };
    const thumb = (v.thumbnail ? v.thumbnail.replace(/(hqdefault|mqdefault)(_live)?/, "maxresdefault") : "./assets/icons/default-thumb.jpg");
    const card = document.createElement("div");
    card.className = "stream-row";
    if (v.section === "live") card.classList.add("onair");

    card.innerHTML = `
      <div class="left">
        <img src="${ch.icon}" class="ch-icon" alt="${ch.name}">
        <div class="ch-name">${ch.name}</div>
      </div>
      <div class="center">
        <h3 class="title" title="${v.title}">${v.title}</h3>
      </div>
      <div class="right">
        <img src="${thumb}" class="thumb" alt="${v.title}"
             onerror="this.src=this.src.replace('maxresdefault','hqdefault')">
      </div>
    `;
    card.addEventListener("click", (e) => { e.stopPropagation(); openModal(v); });
    return card;
  }

  renderAll();

  // ===== モーダル =====
  const modal = document.getElementById("modal");
  const modalCloseBtn = document.querySelector(".modal-close");
  modal.addEventListener("click", (e) => {
    if (e.target === modal) closeModal(); // 背景クリックで閉じる
  });
  modalCloseBtn.addEventListener("click", closeModal);
});

function showError(msg) {
  const sections = document.getElementById("sections");
  sections.innerHTML = `<p style="text-align:center;color:#ff9b9b">${msg}</p>`;
}

function openModal(v) {
  const modal = document.getElementById("modal");
  const body = document.getElementById("modal-body");
  const ch = CHANNEL_MAP[v.channel_id] || { name: v.channel, icon: "./assets/icons/li.jpeg" };
  const thumb = v.thumbnail ? v.thumbnail.replace(/(hqdefault|mqdefault)(_live)?/, "maxresdefault") : "./assets/icons/default-thumb.jpg";
  const scheduled = v.scheduled
    ? new Date(v.scheduled).toLocaleString("ja-JP",{ year:"numeric", month:"long", day:"numeric", hour:"2-digit", minute:"2-digit" })
    : (v.published ? new Date(v.published).toLocaleString("ja-JP") : "日時未定");

  body.innerHTML = `
    <img src="${thumb}" class="modal-thumb"
         onerror="this.src=this.src.replace('maxresdefault','hqdefault')" alt="${v.title}">
    <h2 class="modal-title">${v.title}</h2>
    <p class="modal-channel">📺 ${ch.name}</p>
    <p class="modal-time">🗓 ${scheduled}</p>
    <div class="modal-desc">${(v.description || "説明なし").replace(/</g,"&lt;").replace(/>/g,"&gt;")}</div>
    <div class="modal-footer">
      <div class="footer-left">
        <img src="${ch.icon}" class="footer-icon" alt="${ch.name}">
        <span class="footer-ch">${ch.name}</span>
      </div>
      <a href="${v.url}" target="_blank" class="modal-link">YouTubeで視聴</a>
    </div>
  `;

  modal.style.display = "flex";
  modal.setAttribute("aria-hidden", "false");
  document.body.style.overflow = "hidden";
}

function closeModal() {
  const modal = document.getElementById("modal");
  modal.style.display = "none";
  modal.setAttribute("aria-hidden", "true");
  document.body.style.overflow = "";
}
