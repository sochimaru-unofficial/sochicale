// ==========================
// 🎬 YouTube配信スケジュール表示
// そちまる公式風（live.json + streams.json 統合対応）
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
  // === live.json と streams.json を安全に読み込む ===
  async function loadJson(url) {
    try {
      const res = await fetch(url);
      if (!res.ok) throw new Error(res.statusText);
      return await res.json();
    } catch (e) {
      console.warn(`⚠️ ${url} 読み込み失敗:`, e);
      return {};
    }
  }

  const [liveData, streamData] = await Promise.all([
    loadJson("./data/live.json"),
    loadJson("./data/streams.json")
  ]);

  // === live + streams 統合 ===
  function deepClone(obj) {
    return JSON.parse(JSON.stringify(obj || {}));
  }

  function mergeStreams(live, streams) {
    const merged = deepClone(streams);
    ["live", "upcoming"].forEach(sec => {
      if (Array.isArray(live?.[sec])) merged[sec] = live[sec];
    });
    ["completed", "uploaded"].forEach(sec => {
      if (!Array.isArray(merged[sec])) merged[sec] = [];
    });
    merged.freechat = [];
    return merged;
  }

  const data = mergeStreams(liveData, streamData);
  let currentChannel = "all";

  // ===== チャンネル選択 =====
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
    const liveContainer = document.getElementById("live");
    const completedContainer = document.getElementById("completed");
    const uploadedContainer = document.getElementById("uploaded");
    const freechatContainer = document.getElementById("freechat");

    const liveList = (data.live || []).concat(data.upcoming || []);
    renderCategory(liveContainer, liveList, "live");
    renderCategory(completedContainer, data.completed || [], "completed");
    renderCategory(uploadedContainer, data.uploaded || [], "uploaded");
    renderCategory(freechatContainer, data.freechat || [], "freechat");
  }

  // ==========================
  // 🎨 カテゴリ描画
  // ==========================
  function renderCategory(container, list, key) {
    container.innerHTML = "";
    const filtered = currentChannel === "all" ? list : list.filter(v => v.channel_id === currentChannel);
    if (!filtered.length) {
      container.innerHTML = `<p class="empty">該当する配信はありません。</p>`;
      return;
    }

    filtered.sort((a, b) => {
      const aLive = a.section === "live";
      const bLive = b.section === "live";
      if (aLive && !bLive) return -1;
      if (!aLive && bLive) return 1;
      return (a.scheduled < b.scheduled ? 1 : -1);
    });

    if (key === "live") {
      const liveNow = filtered.filter(v => v.section === "live");
      const upcoming = filtered.filter(v => v.section === "upcoming");

      if (liveNow.length) {
        const header = document.createElement("div");
        header.className = "date-divider live-divider";
        header.textContent = "—— 配信中 ——";
        container.appendChild(header);
        renderByDateGroup(container, liveNow, key);
      }

      if (upcoming.length) {
        const header = document.createElement("div");
        header.className = "date-divider";
        header.textContent = "—— 配信予定 ——";
        container.appendChild(header);
        renderByDateGroup(container, upcoming, key);
      }
    } else {
      renderByDateGroup(container, filtered, key);
    }
  }

    // ==========================
  // 🗓️ 日付ごとにグループ化して描画（JST/土日色分け対応）
  // ==========================
  function renderByDateGroup(container, videos, key) {
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

    Object.keys(groups)
      .sort((a, b) => (a < b ? 1 : -1))
      .forEach(dateKey => {
        if (key !== "freechat") {
          const [_, mm, dd] = dateKey.split("-");
          const m = String(Number(mm));
          const d = String(Number(dd));
          const { label: youbi, className: wdClass } = getJstWeekdayInfo(dateKey);
          const dateHeader = document.createElement("div");
          dateHeader.className = `date-divider ${wdClass}`.trim();
          dateHeader.textContent = `----- ${m}/${d}(${youbi}) -----`;
          container.appendChild(dateHeader);
        }
        groups[dateKey].forEach(v => container.appendChild(createCard(v, key)));
      });
  }

  // === JSTの曜日ラベルとクラス名を返す（prefix付けで衝突回避） ===
  function getJstWeekdayInfo(dateKey) {
    const dt = new Date(`${dateKey}T00:00:00Z`);
    const label = new Intl.DateTimeFormat("ja-JP", {
      weekday: "short",
      timeZone: "Asia/Tokyo"
    }).format(dt);
    let className = "";
    if (label === "土") className = "wd-sat";
    else if (label === "日") className = "wd-sun";
    return { label, className };
  }

  // ==========================
  // 🎴 カード生成（変更なし）
  // ==========================
  function createCard(v, key) {
    const ch = CHANNEL_MAP[v.channel_id] || { name: v.channel, icon: "./assets/icons/li.jpeg" };
    const time = v.scheduled
      ? new Date(v.scheduled).toLocaleTimeString("ja-JP", { hour: "2-digit", minute: "2-digit" })
      : "--:--";
    const thumb = v.thumbnail
      ? v.thumbnail.replace(/(hqdefault|mqdefault)(_live)?/, "maxresdefault")
      : "./assets/icons/default-thumb.jpg";

    const showTime = !["uploaded", "freechat"].includes(key);
    const timeHTML = showTime ? `<div class="time">${time}</div>` : "";

    const card = document.createElement("div");
    card.className = "stream-row";
    if (v.section === "live") card.classList.add("onair");

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
        ${v.section === "live" ? '<span class="onair-badge">ON AIR</span>' : ""}
        <img src="${thumb}" class="thumb"
             onerror="this.src=this.src.replace('maxresdefault','hqdefault')"
             alt="${v.title}">
      </div>
    `;

    card.addEventListener("click", e => {
      e.stopPropagation();
      openModal(v);
    });
    return card;
  }

  renderAll();
});

