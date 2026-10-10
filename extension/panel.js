const $ = (id) => document.getElementById(id);
const DEFAULT_SERVER = "http://localhost:8787";

let state = { server: DEFAULT_SERVER, token: null, teamId: null, me: null, team: null };

function el(tag, props = {}, ...children) {
  const node = Object.assign(document.createElement(tag), props);
  node.append(...children);
  return node;
}

function showMessage(text) {
  $("message").textContent = text || "";
  $("message").hidden = !text;
}

async function api(method, path, body) {
  const res = await fetch(state.server + path, {
    method,
    headers: {
      Authorization: `Bearer ${state.token}`,
      ...(body ? { "Content-Type": "application/json" } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (res.status === 401) {
    await chrome.storage.local.remove("token");
    state.token = null;
    render();
  }
  if (!res.ok) throw new Error(data.error || `Sunucu hatası (${res.status})`);
  return data;
}

// Hata olursa mesajı gösterir; işlem sürerken tetikleyen düğmeyi kilitler.
async function run(button, fn) {
  showMessage("");
  if (button) button.disabled = true;
  try {
    await fn();
  } catch (e) {
    showMessage(e.message);
  } finally {
    if (button) button.disabled = false;
  }
}

// Tarayıcının onay kutusu "bir daha gösterme" ile kalıcı olarak kapatılabildiği için sayfa içi onay.
function ask(text) {
  return new Promise((resolve) => {
    const dialog = $("confirm");
    const done = (answer) => { dialog.close(); resolve(answer); };
    $("confirm-text").textContent = text;
    $("confirm-yes").onclick = () => done(true);
    $("confirm-no").onclick = () => done(false);
    dialog.oncancel = () => resolve(false);
    dialog.showModal();
  });
}

function formatDuration(minutes) {
  if (!minutes) return "kalıcı";
  if (minutes % 1440 === 0) return `${minutes / 1440} gün`;
  if (minutes % 60 === 0) return `${minutes / 60} saat`;
  return `${minutes} dk`;
}

const STATUS_LABEL = {
  ok: "✓",
  failed: "✗",
  pending: "…",
  unbanned: "kaldırıldı",
  unban_failed: "kaldırılamadı",
};

function banCard(ban) {
  const chips = ban.results.map((r) =>
    el("span", {
      className: `chip ${r.status}`,
      title: r.detail || (r.via === "broadcaster" ? "Yayıncının yetkisiyle" : ""),
      textContent: `${STATUS_LABEL[r.status]} ${r.slug}`,
    })
  );
  const card = el("div", { className: `ban${ban.revoked_at ? " revoked" : ""}` },
    el("div", { className: "head" },
      el("strong", { textContent: ban.target_name }),
      el("span", { className: "muted", textContent: formatDuration(ban.duration) })
    ),
    el("div", {
      className: "muted",
      textContent: `${ban.reason || "sebep yok"} · ${ban.created_by} · ${new Date(ban.created_at * 1000).toLocaleString("tr-TR")}`,
    }),
    el("div", { className: "chips" }, ...chips)
  );
  if (!ban.revoked_at) {
    const incomplete = ban.results.some((r) => r.status !== "ok");
    const retry = el("button", { className: "link", textContent: "Tekrar dene", hidden: !incomplete });
    retry.onclick = () => run(retry, async () => {
      await api("POST", `/teams/${state.teamId}/bans/${ban.id}/retry`);
      await loadBans();
    });
    const revoke = el("button", { className: "link", textContent: "Banı kaldır" });
    revoke.onclick = () => run(revoke, async () => {
      if (!(await ask(`${ban.target_name} için ban tüm kanallarda kaldırılsın mı?`))) return;
      await api("DELETE", `/teams/${state.teamId}/bans/${ban.id}`);
      await loadBans();
    });
    card.append(el("div", {}, retry, revoke));
  }
  return card;
}

async function loadBans() {
  const { bans } = await api("GET", `/teams/${state.teamId}/bans`);
  $("tab-list").replaceChildren(
    ...(bans.length ? bans.map(banCard) : [el("p", { className: "muted", textContent: "Liste boş." })])
  );
}

function renderCrew() {
  const team = state.team;
  $("invite").textContent = team.invite_code;
  $("channel-add").hidden = !team.owner;

  $("channels").replaceChildren(...team.channels.map((c) => {
    const item = el("li", {},
      el("span", { className: "grow", textContent: c.slug }),
      el("span", {
        className: "muted",
        textContent: c.broadcaster_joined ? "yayıncı ekipte" : "",
        title: "Yayıncı ekipteyse, moderatör yetkisi yetmediğinde onun yetkisi kullanılır",
      })
    );
    if (team.owner) {
      const remove = el("button", { className: "link", textContent: "Kaldır" });
      remove.onclick = () => run(remove, async () => {
        await api("DELETE", `/teams/${team.id}/channels/${c.broadcaster_id}`);
        await loadTeam();
      });
      item.append(remove);
    }
    return item;
  }));
  if (!team.channels.length) {
    $("channels").append(el("li", { className: "muted", textContent: "Henüz kanal yok." }));
  }

  $("members").replaceChildren(...team.members.map((m) => {
    const item = el("li", {},
      el("span", { className: "grow", textContent: m.name }),
      el("span", { className: "muted", textContent: m.owner ? "sahip" : "" })
    );
    if (team.owner && !m.owner) {
      const remove = el("button", { className: "link", textContent: "Çıkar" });
      remove.onclick = () => run(remove, async () => {
        if (!(await ask(`${m.name} ekipten çıkarılsın mı?`))) return;
        await api("DELETE", `/teams/${team.id}/members/${m.id}`);
        await loadTeam();
      });
      item.append(remove);
    }
    return item;
  }));
}

async function loadTeam() {
  state.team = await api("GET", `/teams/${state.teamId}`);
  renderCrew();
}

function showTab(name) {
  for (const button of document.querySelectorAll("nav button")) {
    button.classList.toggle("active", button.dataset.tab === name);
    $(`tab-${button.dataset.tab}`).hidden = button.dataset.tab !== name;
  }
  if (name === "list") run(null, loadBans);
}

async function selectTeam(teamId) {
  state.teamId = teamId;
  await chrome.storage.local.set({ teamId });
  $("team").value = String(teamId);
  $("team-view").hidden = false;
  $("ban-result").replaceChildren();
  await loadTeam();
}

async function loadMe(preferredTeamId) {
  state.me = await api("GET", "/me");
  $("who").textContent = state.me.user.name;
  const teams = state.me.teams;
  $("team").replaceChildren(...teams.map((t) => el("option", { value: String(t.id), textContent: t.name })));
  $("team").hidden = !teams.length;
  $("team-forms").hidden = teams.length > 0;
  $("team-view").hidden = true;
  if (teams.length) {
    const wanted = teams.find((t) => t.id === preferredTeamId) || teams[0];
    await selectTeam(wanted.id);
  }
}

async function render() {
  const loggedIn = Boolean(state.token);
  $("login-view").hidden = loggedIn;
  $("app-view").hidden = !loggedIn;
  $("logout").hidden = !loggedIn;
  $("server").value = state.server;
  if (!loggedIn) {
    $("who").textContent = "";
    return;
  }
  await run(null, () => loadMe(state.teamId));
}

$("login").onclick = () => run($("login"), async () => {
  const server = ($("server").value.trim() || DEFAULT_SERVER).replace(/\/+$/, "");
  state.server = server;
  await chrome.storage.local.set({ server });
  // Kick penceresi açılınca bu popup kapanabilir; oturum arka planda kaydedilir.
  const res = await chrome.runtime.sendMessage({ type: "login", server });
  if (!res.ok) throw new Error(`Giriş başarısız: ${res.error}`);
});

$("logout").onclick = () => run($("logout"), async () => {
  await api("POST", "/auth/logout").catch(() => {});
  await chrome.storage.local.remove(["token", "teamId"]);
});

$("team").onchange = () => run(null, () => selectTeam(Number($("team").value)));
$("team-menu").onclick = () => { $("team-forms").hidden = !$("team-forms").hidden; };

$("team-create").onsubmit = (event) => {
  event.preventDefault();
  const form = event.target;
  run(form.querySelector("button"), async () => {
    const { id } = await api("POST", "/teams", { name: form.elements.name.value });
    form.reset();
    await loadMe(id);
  });
};

$("team-join").onsubmit = (event) => {
  event.preventDefault();
  const form = event.target;
  run(form.querySelector("button"), async () => {
    const { id } = await api("POST", "/teams/join", { invite_code: form.invite_code.value.trim() });
    form.reset();
    await loadMe(id);
  });
};

$("channel-add").onsubmit = (event) => {
  event.preventDefault();
  const form = event.target;
  run(form.querySelector("button"), async () => {
    await api("POST", `/teams/${state.teamId}/channels`, { slug: form.slug.value });
    form.reset();
    await loadTeam();
  });
};

$("copy-invite").onclick = () => navigator.clipboard.writeText($("invite").textContent);

const MAX_BATCH = 100;

// Satır, virgül ya da boşlukla ayrılmış adları tekilleştirir.
function parseUsernames(text) {
  const seen = new Set();
  return text.split(/[\s,;]+/).map((name) => name.trim()).filter((name) => {
    const key = name.replace(/^@/, "").toLowerCase();
    if (!key || seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

$("tab-ban").onsubmit = (event) => {
  event.preventDefault();
  const form = event.target;
  const button = form.querySelector("button");
  const label = button.textContent;
  const usernames = parseUsernames(form.username.value);
  const count = state.team ? state.team.channels.length : 0;
  if (!count) {
    showMessage("Önce Ekip sekmesinden en az bir kanal ekle.");
    return;
  }
  if (!usernames.length) return;
  if (usernames.length > MAX_BATCH) {
    showMessage(`Tek seferde en fazla ${MAX_BATCH} kullanıcı banlanabilir (${usernames.length} girildi).`);
    return;
  }
  run(button, async () => {
    const who = usernames.length === 1 ? usernames[0] : `${usernames.length} kullanıcı`;
    if (!(await ask(`${who}, ${count} kanalda banlanacak ve ortak listeye eklenecek. Onaylıyor musun?`))) return;
    const reason = form.reason.value.trim();
    const duration = form.duration.value ? Number(form.duration.value) : null;
    const failed = [];
    $("ban-result").replaceChildren();
    try {
      for (const [index, username] of usernames.entries()) {
        button.textContent = `${index + 1} / ${usernames.length}…`;
        try {
          const ban = await api("POST", `/teams/${state.teamId}/bans`, { username, reason, duration });
          $("ban-result").prepend(banCard(ban));
        } catch (e) {
          // Oturum düştüyse kalanları denemenin anlamı yok.
          if (!state.token) throw e;
          failed.push(username);
          $("ban-result").prepend(el("div", { className: "ban" },
            el("strong", { textContent: username }),
            el("div", { className: "chip failed", textContent: e.message })));
        }
      }
    } finally {
      button.textContent = label;
    }
    // Başarısız olanlar düzeltilip yeniden denenebilsin diye alanda kalır.
    form.username.value = failed.join("\n");
    if (!failed.length) form.reason.value = "";
    else showMessage(`${failed.length} kullanıcı banlanamadı; adlar alanda bırakıldı.`);
  });
};

for (const button of document.querySelectorAll("nav button")) {
  button.onclick = () => showTab(button.dataset.tab);
}

chrome.storage.onChanged.addListener((changes) => {
  if ("token" in changes) {
    state.token = changes.token.newValue || null;
    render();
  }
});

(async () => {
  const stored = await chrome.storage.local.get(["server", "token", "teamId"]);
  state.server = stored.server || DEFAULT_SERVER;
  state.token = stored.token || null;
  state.teamId = stored.teamId || null;
  // Sağ tık menüsünden açıldıysa kullanıcı adı hazır gelir.
  $("tab-ban").username.value = new URLSearchParams(location.search).get("user") || "";
  await render();
})();
