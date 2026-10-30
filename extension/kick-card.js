// kick.com'da bir kullanıcının kartı açılınca, ekibin kaç kanalında banlı olduğunu kartın içine yazar.
// Sayfadan yalnızca kartta görünen kullanıcı adını okur; sunucuya isteği service worker atar,
// oturum anahtarı bu sayfaya hiç inmez.
(() => {
  const ROW_ID = "magnetosphere-bans";
  const CACHE_MS = 60 * 1000;
  const cache = new Map(); // ad -> { at, promise }
  let scheduled = false;

  function usernameOf(card) {
    // Kartın başlığındaki ad, kanalın bağlantısıdır: https://kick.com/<slug>
    for (const link of card.querySelectorAll('a[href^="https://kick.com/"]')) {
      const name = new URL(link.href).pathname.split("/").filter(Boolean)[0] || "";
      if (/^[A-Za-z0-9_-]{1,25}$/.test(name)) return name.toLowerCase();
    }
    return null;
  }

  function fetchBans(name) {
    const hit = cache.get(name);
    if (hit && Date.now() - hit.at < CACHE_MS) return hit.promise;
    const promise = chrome.runtime.sendMessage({ type: "userBans", username: name }).catch(() => null);
    cache.set(name, { at: Date.now(), promise });
    return promise;
  }

  function el(tag, cls, text) {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text != null) node.textContent = text;
    return node;
  }

  function untilText(expiresAt) {
    const minutes = Math.max(1, Math.round((expiresAt * 1000 - Date.now()) / 60000));
    if (minutes < 60) return `${minutes} dk kaldı`;
    if (minutes < 60 * 24) return `${Math.round(minutes / 60)} sa kaldı`;
    return `${Math.round(minutes / 60 / 24)} gün kaldı`;
  }

  function fill(row, data) {
    row.replaceChildren();
    if (!data || !data.ok) {
      // Giriş yapılmamış, ekip seçilmemiş ya da sunucuya ulaşılamıyorsa kart sade kalır.
      row.hidden = true;
      return;
    }
    row.hidden = false;
    const { count, permanent, channels, team_channels: total } = data.bans;
    row.classList.toggle("mgs-banned", count > 0);
    const head = el("button", "mgs-head");
    head.type = "button";
    head.append(el("span", "mgs-dot"));
    head.append(el("span", "mgs-count", count > 0 ? `${count} kanaldan banlı` : "Hiçbir kanalda banlı değil"));
    head.title = `Magnetosphere: ekibinin ${total} kanalı arasında`;
    row.append(head);
    if (!count) {
      head.disabled = true;
      return;
    }
    if (permanent !== count) {
      head.append(el("span", "mgs-sub", `${permanent} kalıcı, ${count - permanent} süreli`));
    }
    const list = el("ul", "mgs-list");
    list.hidden = true;
    for (const c of channels) {
      const item = el("li");
      item.append(el("span", null, c.slug));
      item.append(el("span", "mgs-sub", c.expires_at ? untilText(c.expires_at) : "kalıcı"));
      list.append(item);
    }
    head.setAttribute("aria-expanded", "false");
    head.onclick = () => {
      list.hidden = !list.hidden;
      head.setAttribute("aria-expanded", String(!list.hidden));
    };
    row.append(list);
  }

  function update() {
    scheduled = false;
    const card = document.getElementById("user-identity");
    if (!card) return;
    const name = usernameOf(card);
    if (!name) return;
    let row = document.getElementById(ROW_ID);
    // Kick açık kartı başka bir kullanıcıya geçirirken DOM'u yeniden kullanabilir; satır ada bağlıdır.
    if (row && card.contains(row) && row.dataset.user === name) return;
    row?.remove();
    // Joined / Followed satırının hemen altı; bulunamazsa adın altı.
    const anchor = card.querySelector(".grid.auto-cols-fr") || card.querySelector('a[href^="https://kick.com/"]')?.parentElement;
    if (!anchor) return;
    row = el("div");
    row.id = ROW_ID;
    row.dataset.user = name;
    row.hidden = true;
    anchor.after(row);
    fetchBans(name).then((data) => {
      if (row.isConnected && row.dataset.user === name) fill(row, data);
    });
  }

  new MutationObserver(() => {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(update);
  }).observe(document.body, { childList: true, subtree: true });

  // Panelde ekip değişince ya da çıkış yapılınca önbellekteki sayılar geçersizdir.
  chrome.storage.onChanged.addListener((changes, area) => {
    if (area !== "local" || !("token" in changes || "teamId" in changes || "server" in changes)) return;
    cache.clear();
    document.getElementById(ROW_ID)?.remove();
    update();
  });
})();
