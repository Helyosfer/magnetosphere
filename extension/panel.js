const $ = (id) => document.getElementById(id);
const DEFAULT_SERVER = "http://localhost:8787";
const MAX_IMPORT = 5000;
// Bundan uzun listeler sunucudaki sıraya gider; panel kapansa da işlenmeye devam eder.
const QUEUE_THRESHOLD = 10;

let state = { server: DEFAULT_SERVER, token: null, teamId: null, me: null, team: null, list: { bans: [], matched: 0, active_total: 0 } };

function el(tag, props = {}, ...children) {
  const node = Object.assign(document.createElement(tag), props);
  node.append(...children);
  return node;
}

function showMessage(text, kind = "error") {
  $("message").textContent = text || "";
  $("message").className = `banner ${kind}`;
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
  if (!minutes) return "Kalıcı";
  if (minutes % 1440 === 0) return `${minutes / 1440} gün`;
  if (minutes % 60 === 0) return `${minutes / 60} saat`;
  return `${minutes} dk`;
}

function formatDate(seconds) {
  return new Date(seconds * 1000).toLocaleString("tr-TR", {
    day: "numeric", month: "short", hour: "2-digit", minute: "2-digit",
  });
}

const STATUS_TITLE = {
  ok: "Banlandı",
  failed: "Banlanamadı",
  pending: "Henüz uygulanmadı",
  unbanned: "Ban kaldırıldı",
  unban_failed: "Ban kaldırılamadı",
};

function banCard(ban) {
  const applied = ban.results.filter((r) => r.status === "ok").length;
  const complete = applied === ban.results.length;
  const chips = ban.results.map((r) => {
    const via = r.via === "broadcaster" && r.status === "ok" ? " (yayıncı yetkisiyle)" : "";
    return el("span", {
      className: `chip ${r.status}`,
      title: `${STATUS_TITLE[r.status]}${via}${r.detail ? ` — ${r.detail}` : ""}`,
      textContent: r.slug,
    });
  });
  const tag = ban.revoked_at
    ? el("span", { className: "tag off", textContent: "Kaldırıldı" })
    : el("span", { className: `tag ${ban.duration ? "timed" : "perm"}`, textContent: formatDuration(ban.duration) });

  const card = el("div", { className: `ban${ban.revoked_at ? " revoked" : complete ? "" : " partial"}` },
    el("div", { className: "head" }, el("span", { className: "name", textContent: ban.target_name }), tag),
    el("div", { className: `reason${ban.reason ? "" : " none"}`, textContent: ban.reason || "Sebep belirtilmedi" }),
    el("div", { className: "meta", textContent: `${ban.created_by} · ${formatDate(ban.created_at)}` })
  );
  const foot = el("div", { className: "foot" }, el("div", { className: "chips" }, ...chips));
  if (!ban.revoked_at) {
    const actions = el("div", { className: "actions" });
    if (!complete) {
      const retry = el("button", { className: "ghost small", textContent: "Tekrar dene" });
      retry.onclick = () => run(retry, async () => {
        await api("POST", `/teams/${state.teamId}/bans/${ban.id}/retry`);
        await loadBans();
      });
      actions.append(retry);
    }
    const revoke = el("button", { className: "ghost small", textContent: "Kaldır" });
    revoke.onclick = () => run(revoke, async () => {
      if (!(await ask(`${ban.target_name} için ban tüm kanallarda kaldırılsın mı?`))) return;
      await api("DELETE", `/teams/${state.teamId}/bans/${ban.id}`);
      await loadBans();
    });
    actions.append(revoke);
    foot.append(actions);
  }
  card.append(foot);
  return card;
}

function renderBans() {
  const { bans, matched, active_total: activeTotal } = state.list;
  $("list-count").textContent = activeTotal;
  $("list-count").hidden = !activeTotal;

  const searching = $("list-search").value.trim();
  const empty = searching ? "Aramayla eşleşen kayıt yok." : "Ortak liste boş. İlk banı Banla sekmesinden at.";
  const cards = bans.length ? bans.map(banCard) : [el("div", { className: "empty", textContent: empty })];
  if (matched > bans.length) {
    cards.push(el("p", {
      className: "muted small",
      textContent: `${matched} kayıttan en yeni ${bans.length} tanesi gösteriliyor. Diğerleri için arama yap.`,
    }));
  }
  $("ban-list").replaceChildren(...cards);
}

async function loadBans() {
  const params = new URLSearchParams();
  const query = $("list-search").value.trim();
  if (query) params.set("q", query);
  if ($("list-revoked").checked) params.set("revoked", "1");
  const teamId = state.teamId;
  const list = await api("GET", `/teams/${teamId}/bans?${params}`);
  if (teamId !== state.teamId) return;
  state.list = list;
  renderBans();
}

function renderTeam() {
  const team = state.team;
  const slugs = team.channels.map((c) => c.slug);
  $("targets").textContent = slugs.length
    ? `${slugs.length} kanala uygulanacak: ${slugs.join(", ")}`
    : "Ekipte henüz kanal yok. Önce Ekip sekmesinden kanal ekle.";
  $("ban-submit").textContent = slugs.length > 1 ? `${slugs.length} kanalda banla` : "Banla";

  $("invite").textContent = team.invite_code;
  $("channel-add").hidden = !team.owner;
  $("rotate-invite").hidden = !team.owner;
  $("channel-count").textContent = team.channels.length;
  $("member-count").textContent = team.members.length;

  $("channels").replaceChildren(...team.channels.map((c) => {
    const item = el("li", {}, el("span", { className: "grow mono", textContent: c.slug }));
    if (c.broadcaster_joined) {
      item.append(el("span", {
        className: "tag off",
        textContent: "Yayıncı ekipte",
        title: "Moderatör yetkisi yetmediğinde yayıncının yetkisi kullanılır",
      }));
    }
    if (team.owner) {
      const remove = el("button", { className: "ghost small", textContent: "Kaldır" });
      remove.onclick = () => run(remove, async () => {
        if (!(await ask(`${c.slug} kanalı ekipten kaldırılsın mı? Mevcut banlar Kick'te kalır.`))) return;
        await api("DELETE", `/teams/${team.id}/channels/${c.broadcaster_id}`);
        await loadTeam();
        await loadBans();
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
      el("span", { className: "avatar", textContent: m.name.slice(0, 1).toUpperCase() }),
      el("span", { className: "grow", textContent: m.name })
    );
    if (m.owner) item.append(el("span", { className: "tag off", textContent: "Sahip" }));
    if (team.owner && !m.owner) {
      const remove = el("button", { className: "ghost small", textContent: "Çıkar" });
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
  renderTeam();
}

function showTab(name) {
  for (const button of document.querySelectorAll(".tabs button")) {
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
  await loadBans();
  await pollQueue();
}

const PROBLEM_LABEL = {
  notfound: "Kick'te bulunamadı",
  rejected: "reddedildi",
  partial: "bazı kanallarda tutmadı",
  error: "hata",
};

let queueTimer = null;
let queueProblems = [];

function renderQueue(status) {
  const counts = status.counts;
  const pending = counts.pending || 0;
  const processed = status.total - pending;
  queueProblems = status.problems;
  $("queue").hidden = !status.total;
  if (!status.total) return;

  $("queue-progress").textContent = `${processed} / ${status.total}`;
  $("queue-bar").style.width = `${Math.round((processed / status.total) * 100)}%`;
  const parts = [`${(counts.done || 0) + (counts.partial || 0)} banlandı`];
  if (counts.notfound) parts.push(`${counts.notfound} bulunamadı`);
  if (counts.rejected) parts.push(`${counts.rejected} reddedildi`);
  if (counts.error) parts.push(`${counts.error} hata`);
  $("queue-summary").textContent =
    (pending ? `${pending} kullanıcı sırada. Paneli kapatabilirsin, işlem sürer. ` : "Sıra tamamlandı. ") + parts.join(" · ");

  $("queue-problems").hidden = !queueProblems.length;
  $("queue-problems").querySelector("summary").textContent = `${queueProblems.length} sorunlu kayıt`;
  $("queue-problem-list").replaceChildren(...queueProblems.map((p) => el("li", {},
    el("span", { className: "grow mono", textContent: p.name }),
    el("span", { className: "muted", textContent: p.detail || PROBLEM_LABEL[p.status], title: p.detail })
  )));
  $("queue-copy").hidden = !queueProblems.some((p) => p.status === "notfound");
  $("queue-cancel").hidden = !pending;
  $("queue-clear").hidden = Boolean(pending);
}

async function pollQueue() {
  clearTimeout(queueTimer);
  const teamId = state.teamId;
  const status = await api("GET", `/teams/${teamId}/imports`);
  if (teamId !== state.teamId) return;
  renderQueue(status);
  if (status.counts.pending) {
    queueTimer = setTimeout(() => run(null, async () => {
      await pollQueue();
      await loadBans();
    }), 3000);
  }
}

$("queue-cancel").onclick = () => run($("queue-cancel"), async () => {
  if (!(await ask("Sırada bekleyen kullanıcılar iptal edilsin mi? Şimdiye kadar atılan banlar kalır."))) return;
  await api("DELETE", `/teams/${state.teamId}/imports/pending`);
  await pollQueue();
});

$("queue-clear").onclick = () => run($("queue-clear"), async () => {
  await api("DELETE", `/teams/${state.teamId}/imports/finished`);
  await pollQueue();
});

$("queue-copy").onclick = async () => {
  const names = queueProblems.filter((p) => p.status === "notfound").map((p) => p.name);
  await navigator.clipboard.writeText(names.join("\n"));
  showMessage(`${names.length} kullanıcı adı kopyalandı.`, "info");
};

// .csv dosyalarında yalnızca ilk sütun alınır; başlık satırı varsa atlanır.
function namesFromFile(name, text) {
  if (!/\.csv$/i.test(name)) return text;
  const cells = text.split(/\r?\n/).map((line) => line.split(/[,;\t]/)[0].trim());
  if (/^["']?(kullan|user|name|nick|ad\b)/i.test(cells[0] || "")) cells.shift();
  return cells.join("\n");
}

$("file-pick").onclick = () => $("file-input").click();

$("file-input").onchange = () => run($("file-pick"), async () => {
  const files = [...$("file-input").files];
  const texts = await Promise.all(files.map(async (file) => namesFromFile(file.name, await file.text())));
  const before = parseUsernames($("username").value).length;
  $("username").value = parseUsernames([$("username").value, ...texts].join("\n")).join("\n");
  $("file-input").value = "";
  updateNameCount();
  const added = parseUsernames($("username").value).length - before;
  showMessage(`${files.map((f) => f.name).join(", ")}: ${added} kullanıcı yüklendi.`, "info");
});

async function loadMe(preferredTeamId) {
  state.me = await api("GET", "/me");
  $("who").textContent = state.me.user.name;
  $("avatar").textContent = state.me.user.name.slice(0, 1).toUpperCase();
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
  $("user").hidden = !loggedIn;
  $("server").value = state.server;
  if (loggedIn) await run(null, () => loadMe(state.teamId));
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
    await loadBans();
  });
};

$("copy-invite").onclick = async () => {
  await navigator.clipboard.writeText($("invite").textContent);
  showMessage("Davet kodu kopyalandı.", "info");
};

$("rotate-invite").onclick = () => run($("rotate-invite"), async () => {
  if (!(await ask("Davet kodu yenilensin mi? Eski kod artık çalışmaz; mevcut üyeler etkilenmez."))) return;
  await api("POST", `/teams/${state.teamId}/invite`);
  await loadTeam();
  showMessage("Davet kodu yenilendi.", "info");
});

let searchTimer = null;
$("list-search").oninput = () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => run(null, loadBans), 250);
};
$("list-revoked").onchange = () => run(null, loadBans);

// Satır, virgül ya da boşlukla ayrılmış adları tekilleştirir; tırnak ve köşeli parantezleri yok sayar.
function parseUsernames(text) {
  const seen = new Set();
  return text.replace(/["'[\]]/g, " ").split(/[\s,;]+/).map((name) => name.trim()).filter((name) => {
    const key = name.replace(/^@/, "").toLowerCase();
    if (!key || seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function updateNameCount() {
  const count = parseUsernames($("username").value).length;
  $("name-count").textContent = `${count} kullanıcı`;
  $("name-count").hidden = count < 2;
}

$("username").oninput = updateNameCount;

for (const preset of $("reason-presets").children) {
  preset.onclick = () => { $("reason").value = preset.textContent; };
}

$("tab-ban").onsubmit = (event) => {
  event.preventDefault();
  const form = event.target;
  const button = $("ban-submit");
  const label = button.textContent;
  const usernames = parseUsernames(form.username.value);
  const count = state.team ? state.team.channels.length : 0;
  if (!count) {
    showMessage("Önce Ekip sekmesinden en az bir kanal ekle.");
    return;
  }
  if (!usernames.length) return;
  if (usernames.length > MAX_IMPORT) {
    showMessage(`Tek seferde en fazla ${MAX_IMPORT} kullanıcı gönderilebilir (${usernames.length} girildi).`);
    return;
  }
  run(button, async () => {
    const who = usernames.length === 1 ? usernames[0] : `${usernames.length} kullanıcı`;
    const reason = form.reason.value.trim();
    const duration = form.duration.value ? Number(form.duration.value) : null;
    const how = duration ? `${formatDuration(duration)} süreyle` : "kalıcı olarak";
    if (usernames.length > QUEUE_THRESHOLD) {
      if (!(await ask(`${who} sıraya alınacak ve ${count} kanalda ${how} banlanacak. Paneli kapatsan da işlem sürer. Onaylıyor musun?`))) return;
      const { added, skipped } = await api("POST", `/teams/${state.teamId}/imports`, { usernames, reason, duration });
      form.username.value = "";
      form.reason.value = "";
      updateNameCount();
      $("ban-result").replaceChildren();
      showMessage(`${added} kullanıcı sıraya alındı${skipped ? `, ${skipped} tanesi zaten sıradaydı` : ""}.`, "info");
      await pollQueue();
      return;
    }
    if (!(await ask(`${who}, ${count} kanalda ${how} banlanacak ve ortak listeye eklenecek. Onaylıyor musun?`))) return;
    const failed = [];
    $("ban-result").replaceChildren();
    try {
      for (const [index, username] of usernames.entries()) {
        button.textContent = `${index + 1} / ${usernames.length} banlanıyor…`;
        try {
          const ban = await api("POST", `/teams/${state.teamId}/bans`, { username, reason, duration });
          $("ban-result").prepend(banCard(ban));
        } catch (e) {
          // Oturum düştüyse kalanları denemenin anlamı yok.
          if (!state.token) throw e;
          failed.push(username);
          $("ban-result").prepend(el("div", { className: "ban error" },
            el("div", { className: "head" }, el("span", { className: "name", textContent: username })),
            el("div", { className: "reason", textContent: e.message })));
        }
      }
    } finally {
      button.textContent = label;
    }
    // Başarısız olanlar düzeltilip yeniden denenebilsin diye alanda kalır.
    form.username.value = failed.join("\n");
    updateNameCount();
    if (!failed.length) form.reason.value = "";
    else showMessage(`${failed.length} kullanıcı banlanamadı; adlar alanda bırakıldı.`);
    await loadBans();
  });
};

for (const button of document.querySelectorAll(".tabs button")) {
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
  $("username").value = new URLSearchParams(location.search).get("user") || "";
  await render();
})();
