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

  // ===== 描画 =====
  function renderAll() {
    const live = document.getElementById("live");
    const completed = document.getElementById("completed");
    const uploaded = document.getElementById("uploaded");
    const freechat = document.getElementById("freechat");

    renderCategory(live, [...(data.live || []), ...(data.upcoming || [])]);
    renderCategory(completed, data.completed || []);
    renderCategory(uploaded, data.uploaded || []);
    renderCategory(freechat, data.freechat || []);
  }

  function renderCategory(container, list) {
    container.innerHTML = "";
    if (!list.length) return;
    list.forEach(v => container.appendChild(createCard(v)));
  }

  function createCard(v) {
    const ch = CHANNEL_MAP[v.channel_id] || { name: v.channel, icon: "./assets/icons/li.jpeg" };
    const thumb = v.thumbnail || "./assets/icons/default-thumb.jpg";
    const card = document.createElement("div");
    card.className = "stream-row";
    card.innerHTML = `
      <div class="left">
        <img src="${ch.icon}" class="ch-icon">
        <div class="ch-name">${ch.name}</div>
      </div>
      <div class="center"><div class="title">${v.title}</div></div>
      <div class="right"><img src="${thumb}" class="thumb"></div>`;
    card.addEventListener("click", () => openModal(v));
    return card;
  }

  renderAll();
});

// ===== モーダル =====
function openModal(v) {
  const modal = document.getElementById("modal");
  const body = document.getElementById("modal-body");
  const ch = CHANNEL_MAP[v.channel_id] || { name: v.channel, icon: "./assets/icons/li.jpeg" };
  const thumb = v.thumbnail || "./assets/icons/default-thumb.jpg";

  body.innerHTML = `
    <button class="modal-close" onclick="closeModal()">×</button>
    <img src="${thumb}" class="modal-thumb">
    <h2 class="modal-title">${v.title}</h2>
    <p class="modal-channel">${ch.name}</p>
    <p class="modal-desc">${v.description || "説明なし"}</p>
    <div class="modal-footer">
      <div class="footer-left">
        <img src="${ch.icon}" class="footer-icon">
        <span>${ch.name}</span>
      </div>
      <a href="${v.url}" target="_blank" class="modal-link">YouTubeで視聴</a>
    </div>`;
  modal.style.display = "flex";
}

function closeModal() {
  document.getElementById("modal").style.display = "none";
}
