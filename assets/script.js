document.addEventListener("DOMContentLoaded", async () => {
  const data = await fetch("./data/streams.json").then(res => res.json());
  const categories = ["live", "upcoming", "completed"];

  categories.forEach(key => {
    const container = document.getElementById(key);
    const list = data[key] || [];
    list.sort((a, b) => (a.scheduled < b.scheduled ? 1 : -1));

    list.forEach(v => {
      const cid = Object.keys(CHANNEL_MAP).find(id => v.url.includes(id));
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
