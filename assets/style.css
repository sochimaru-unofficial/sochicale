document.addEventListener("DOMContentLoaded", async () => {
  const data = await fetch("data/streams.json").then(res => res.json());
  const categories = ["live", "upcoming", "completed"];

  categories.forEach(key => {
    const container = document.getElementById(key);
    const list = data[key] || [];
    list.sort((a, b) => (a.scheduled > b.scheduled ? 1 : -1));
    list.forEach(v => {
      const card = document.createElement("div");
      card.className = "card";
      card.innerHTML = `
        <img src="${v.thumbnail}" class="thumb">
        <div class="info">
          <p class="channel">${v.channel}</p>
          <h3>${v.title}</h3>
          <p class="time">${v.scheduled || "日時不明"}</p>
          <div class="desc">${v.description}</div>
        </div>
      `;
      card.addEventListener("click", e => {
        e.stopPropagation();
        openModal(v);
      });
      container.appendChild(card);
    });
  });

  document.querySelectorAll(".section-header").forEach(btn => {
    btn.addEventListener("click", e => {
      const target = document.getElementById(btn.dataset.target);
      target.style.display = target.style.display === "flex" ? "none" : "flex";
    });
  });
});

function openModal(v) {
  const modal = document.getElementById("modal");
  const body = document.getElementById("modal-body");
  body.innerHTML = `
    <img src="${v.thumbnail}" style="width:100%; border-radius:6px; margin-bottom:10px;">
    <h2>${v.title}</h2>
    <p style="color:#0070f3; font-weight:600;">${v.channel}</p>
    <p style="white-space: pre-wrap; line-height:1.6;">${v.description}</p>
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
