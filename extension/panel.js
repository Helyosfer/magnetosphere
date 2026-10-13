const $ = (id) => document.getElementById(id);
const DEFAULT_SERVER = "https://magnetosphere.helyosfer.me";
const MAX_IMPORT = 5000;
// Bundan uzun listeler sunucudaki sıraya gider; panel kapansa da işlenmeye devam eder.
const QUEUE_THRESHOLD = 10;

// Ekip içi roller, yetkiye göre sıralı (sunucudaki ROLES ile aynı).
const ROLE_RANK = { viewer: 0, mod: 1, admin: 2, owner: 3 };
const ROLE_LABEL = { owner: "Sahip", admin: "Yönetici", mod: "Moderatör", viewer: "İzleyici" };
// Rol bilgisi göndermeyen eski sunucularda sahip dışındaki herkes moderatör sayılır.
const roleOf = (item) => item.role || (item.owner ? "owner" : "mod");
const can = (need) => ROLE_RANK[roleOf(state.team)] >= ROLE_RANK[need];

let state = { server: DEFAULT_SERVER, token: null, teamId: null, me: null, team: null, list: { bans: [], matched: 0, active_total: 0 } };

function el(tag, props = {}, ...children) {
  const node = Object.assign(document.createElement(tag), props);
  node.append(...children);
  return node;
}

function icon(name) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("class", "icon");
  svg.setAttribute("aria-hidden", "true");
  svg.append(document.createElementNS("http://www.w3.org/2000/svg", "use"));
  svg.firstChild.setAttribute("href", `#i-${name}`);
  return svg;
}

function emptyState(iconName, title, hint, tag = "div") {
  return el(tag, { className: "empty" }, icon(iconName), el("strong", { textContent: title }), el("span", { className: "small", textContent: hint }));
}

const TOAST_MS = 3200;
let toastTimer = null;

// Hatalar şeritte kalır; başarı bildirimi ("info") kendiliğinden kaybolan toast olur.
function showMessage(text, kind = "error") {
  if (kind === "info") {
    const toast = $("toast");
    clearTimeout(toastTimer);
    $("toast-text").textContent = text;
    toast.classList.remove("leaving");
    toast.hidden = false;
    toastTimer = setTimeout(() => {
      toast.classList.add("leaving");
      toastTimer = setTimeout(() => { toast.hidden = true; }, 200);
    }, TOAST_MS);
    return;
  }
  $("message-text").textContent = text || "";
  $("message").hidden = !text;
}

$("message-close").onclick = () => showMessage("");

async function api(method, path, body) {
  let res;
  try {
    res = await fetch(state.server + path, {
      method,
      headers: {
        Authorization: `Bearer ${state.token}`,
        ...(body ? { "Content-Type": "application/json" } : {}),
      },
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    // Tarayıcının "Failed to fetch" hatası kullanıcıya bir şey söylemez.
    throw new Error("Sunucuya ulaşılamadı. İnternet bağlantını kontrol edip tekrar dene.");
  }
  const data = await res.json().catch(() => ({}));
  if (res.status === 401) {
    await chrome.storage.local.remove("token");
    state.token = null;
    render();
  }
  if (!res.ok) throw new Error(data.error || `Sunucu şu an yanıt veremiyor (${res.status}). Biraz sonra tekrar dene.`);
  return data;
}

// Hata olursa mesajı gösterir; işlem sürerken tetikleyen düğmeyi kilitler.
// data-busy, "işlem sürüyor" kilidini "kullanılamaz" kilidinden ayırır (CSS'te farklı görünürler).
async function run(button, fn) {
  showMessage("");
  if (button) {
    button.disabled = true;
    button.dataset.busy = "";
  }
  try {
    await fn();
  } catch (e) {
    showMessage(e.message);
  } finally {
    if (button) {
      button.disabled = false;
      delete button.dataset.busy;
    }
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
    day: "numeric", month: "long", year: "numeric", hour: "2-digit", minute: "2-digit",
  });
}

// "3 dk önce" gibi göreli zaman; bir haftadan eskiler kısa tarihle gösterilir.
function formatAgo(seconds) {
  const diff = Math.max(0, Date.now() / 1000 - seconds);
  if (diff < 45) return "az önce";
  if (diff < 3600) return `${Math.max(1, Math.round(diff / 60))} dk önce`;
  if (diff < 86400) return `${Math.round(diff / 3600)} sa önce`;
  if (diff < 7 * 86400) return `${Math.round(diff / 86400)} gün önce`;
  const date = new Date(seconds * 1000);
  const sameYear = date.getFullYear() === new Date().getFullYear();
  return date.toLocaleDateString("tr-TR", { day: "numeric", month: "short", ...(sameYear ? {} : { year: "numeric" }) });
}

function timeEl(seconds) {
  const node = el("time", { dateTime: new Date(seconds * 1000).toISOString(), title: formatDate(seconds), textContent: formatAgo(seconds) });
  node.dataset.ts = seconds;
  return node;
}

// Panel açık kaldıkça göreli zamanlar eskimesin.
setInterval(() => {
  for (const node of document.querySelectorAll("time[data-ts]")) node.textContent = formatAgo(Number(node.dataset.ts));
}, 30000);

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
    el("div", { className: "meta" },
      el("span", { className: "avatar mini", textContent: ban.created_by.slice(0, 1).toUpperCase() }),
      el("span", { className: "who", textContent: ban.created_by }),
      "·",
      timeEl(ban.created_at))
  );
  const foot = el("div", { className: "foot" }, el("div", { className: "chips" }, ...chips));
  // Moderatör yalnızca kendi attığı banı kaldırabilir; başkasınınkini sahip ve yöneticiler kaldırır.
  const mine = ban.created_by_id === undefined || ban.created_by_id === state.me.user.id;
  if (!ban.revoked_at && can("mod")) {
    const actions = el("div", { className: "actions" });
    if (!complete) {
      const retry = el("button", { className: "ghost small", textContent: "Tekrar dene" });
      retry.onclick = () => run(retry, async () => {
        await api("POST", `/teams/${state.teamId}/bans/${ban.id}/retry`);
        await loadBans();
      });
      actions.append(retry);
    }
    if (mine || can("admin")) {
      const revoke = el("button", { className: "ghost small", textContent: "Kaldır" });
      revoke.onclick = () => run(revoke, async () => {
        if (!(await ask(`${ban.target_name} için ban tüm kanallarda kaldırılsın mı?`))) return;
        await api("DELETE", `/teams/${state.teamId}/bans/${ban.id}`);
        await loadBans();
      });
      actions.append(revoke);
    }
    if (actions.children.length) foot.append(actions);
  }
  card.append(foot);
  return card;
}

function renderBans() {
  const { bans, matched, active_total: activeTotal } = state.list;
  $("list-count").textContent = activeTotal;
  $("list-count").hidden = !activeTotal;

  const searching = $("list-search").value.trim();
  const empty = searching
    ? emptyState("search", "Eşleşen kayıt yok", "Başka bir kullanıcı adı ya da sebep dene.")
    : emptyState("shield", "Ortak liste boş", "İlk banı Banla sekmesinden at; burada görünür.");
  const cards = bans.length ? bans.map(banCard) : [empty];
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
  // Ekibin listesi ilk kez gelirken iskelet; sonraki yenilemelerde eldeki kartlar yerinde kalır.
  if (!state.listLoaded) $("ban-list").replaceChildren(...[0, 1, 2].map(skeletonCard));
  let list;
  try {
    list = await api("GET", `/teams/${teamId}/bans?${params}`);
  } catch (e) {
    if (teamId === state.teamId && !state.listLoaded) {
      $("ban-list").replaceChildren(emptyState("alert", "Liste yüklenemedi", "Sekmeye yeniden tıklayarak tekrar dene."));
    }
    throw e;
  }
  if (teamId !== state.teamId) return;
  state.list = list;
  state.listLoaded = true;
  renderBans();
}

function skeletonCard() {
  const line = (width) => {
    const node = el("div", { className: "sk" });
    node.style.width = width;
    return node;
  };
  return el("div", { className: "ban skeleton", ariaHidden: "true" }, line("45%"), line("70%"), line("35%"));
}

function renderTeam() {
  const team = state.team;
  const me = state.me.user;
  const [mod, admin, owner] = [can("mod"), can("admin"), can("owner")];
  const slugs = team.channels.map((c) => c.slug);
  $("viewer-note").hidden = mod;
  $("ban-fields").hidden = !mod;
  if (slugs.length) {
    $("targets").textContent = `${slugs.length} kanala uygulanacak: ${slugs.join(", ")}`;
  } else if (admin) {
    const add = el("button", { type: "button", className: "link", textContent: "Kanal ekle" });
    add.onclick = () => {
      showTab("crew");
      $("channel-add").elements.slug.focus();
    };
    $("targets").replaceChildren("Ekipte henüz kanal yok. ", add);
  } else {
    $("targets").textContent = "Ekipte henüz kanal yok. Kanalları ekip sahibi ve yöneticiler ekleyebilir.";
  }
  $("ban-submit").textContent = slugs.length > 1 ? `${slugs.length} kanalda banla` : "Banla";
  $("ban-submit").disabled = !slugs.length;

  $("channel-add").hidden = !admin;
  $("channel-count").textContent = team.channels.length;
  $("member-count").textContent = team.members.length;

  // Kick'te kanal kimliği kullanıcı kimliğiyle aynı; kendi kanalı listede yoksa tek tıkla eklenebilsin.
  const own = team.channels.find((c) => c.broadcaster_id === me.id);
  $("channel-self").hidden = !admin || Boolean(own);
  $("channel-self-text").textContent = `Kendi kanalın (${me.name}) listede değil; orada ban atılmaz.`;

  // Yetki paylaşımı yalnızca kanalı bu ekibin listesinde olan üyeye sorulur; kararı yalnızca o verir.
  $("lend-card").hidden = !own || team.lend === undefined;
  $("lend").checked = Boolean(team.lend);

  $("invite-card").hidden = !admin;
  $("invite").textContent = team.invite_code;
  $("invite-text").textContent = team.join_role === "viewer"
    ? "Bu kodla katılanlar izleyici olarak başlar: listeyi görür, sahip rol verene dek ban atamaz."
    : "Bu kodu alan herkes ekibe moderatör olarak katılıp ekibin kanallarında ban atabilir. Yalnızca güvendiğin kişilerle paylaş.";
  $("join-role-row").hidden = !owner || team.join_role === undefined;
  $("join-role").value = team.join_role || "mod";
  $("team-leave-card").hidden = owner || team.role === undefined;
  $("team-danger").hidden = !owner;

  $("channels").replaceChildren(...team.channels.map((c) => {
    const item = el("li", {}, el("span", { className: "grow mono", textContent: c.slug }));
    if (c.broadcaster_joined) {
      item.append(el("span", {
        className: "tag off",
        textContent: "Yayıncı yetkisi açık",
        title: "Moderatör yetkisi yetmediğinde ban, ekipteki yayıncının yetkisiyle uygulanır",
      }));
    } else if (c.broadcaster_member) {
      item.append(el("span", {
        className: "tag off",
        textContent: "Yayıncı ekipte",
        title: "Yayıncı ekipte ama yetkisini paylaşmıyor; ban yalnızca orada moderatör olanların yetkisiyle tutar",
      }));
    }
    if (admin) {
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
    $("channels").append(emptyState("channel", "Henüz kanal yok",
      admin ? "Moderatörü olduğun kanalları aşağıdan ekle." : "Kanalları ekip sahibi ve yöneticiler ekleyebilir.", "li"));
  }

  $("members").replaceChildren(...team.members.map((m) => {
    const role = roleOf(m);
    const item = el("li", {},
      el("span", { className: "avatar", textContent: m.name.slice(0, 1).toUpperCase() }),
      el("span", { className: "grow" }, m.name, m.id === me.id ? el("span", { className: "you", textContent: " (sen)" }) : "")
    );
    if (owner && role !== "owner" && team.role !== undefined) {
      // Sahip, diğer üyelerin rolünü buradan değiştirir; son seçenek sahipliği devreder.
      const select = el("select", { className: "small", ariaLabel: `${m.name} için rol` },
        ...["admin", "mod", "viewer"].map((r) => el("option", { value: r, textContent: ROLE_LABEL[r], selected: r === role })),
        el("option", { value: "owner", textContent: "Sahipliği devret…" }));
      select.onchange = () => run(null, async () => {
        const next = select.value;
        try {
          if (next === "owner" && !(await ask(`Sahiplik ${m.name} adlı üyeye devredilsin mi? Sen yönetici olursun; bunu yalnızca yeni sahip geri alabilir.`))) return;
          await api("POST", `/teams/${team.id}/members/${m.id}/role`, { role: next });
          showMessage(next === "owner" ? `Sahiplik ${m.name} adlı üyeye devredildi.` : `${m.name} artık ${ROLE_LABEL[next].toLocaleLowerCase("tr")}.`, "info");
        } finally {
          await loadTeam();   // vazgeçilirse ya da hata olursa seçim eski haline döner
        }
      });
      item.append(select);
    } else {
      item.append(el("span", { className: "tag off", textContent: ROLE_LABEL[role] }));
    }
    if (admin && m.id !== me.id && ROLE_RANK[role] < ROLE_RANK[roleOf(team)]) {
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
  state.listLoaded = false;
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
  $("queue").classList.toggle("active", pending > 0);
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
  $("queue-cancel").hidden = !pending || !can("mod");
  $("queue-clear").hidden = Boolean(pending) || !can("mod");
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
  $("teambar").hidden = !teams.length;
  $("team-forms").hidden = teams.length > 0;
  $("team-menu").setAttribute("aria-expanded", String(!teams.length));
  $("team-view").hidden = true;
  // Ekip kurmanın kapalı olduğu sunucuda kullanıcıya yalnızca davet koduyla katılma yolu gösterilir.
  const canCreate = state.me.can_create_team !== false;
  // İlk girişte tek tıkla kendi listesini kurar; adını kendi seçeceği ekipler "+ Ekip" menüsünde.
  $("team-create").hidden = !canCreate || !teams.length;
  $("solo-start").hidden = !canCreate;
  $("solo-hint").hidden = !canCreate;
  $("welcome").hidden = teams.length > 0;
  $("welcome-title").textContent = `Hoş geldin, ${state.me.user.name}!`;
  $("welcome-text").textContent = canCreate
    ? "Kimseyi davet etmen gerekmez: moderatörü olduğun kanalları ekle, bir kullanıcıyı hepsinde birden banla."
    : "Başlamak için ekibinden bir davet kodu iste ve aşağıya yapıştır.";
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
  if (!loggedIn) return;
  // Sunucu yanıt verene dek boş panel yerine iskelet görünür.
  showMessage("");
  $("app-view").classList.remove("failed");
  $("app-view").classList.add("loading");
  try {
    await loadMe(state.teamId);
  } catch (e) {
    // Oturum düştüyse giriş ekranı zaten açılmıştır; diğer durumda yarım panel yerine tekrar deneme sunulur.
    if (state.token) {
      $("load-error-text").textContent = e.message;
      $("app-view").classList.add("failed");
    }
  }
  $("load-error").hidden = !$("app-view").classList.contains("failed");
  $("app-view").classList.remove("loading");
}

$("load-retry").onclick = () => render();

// Chrome'un İngilizce giriş hataları kullanıcının anlayacağı dile çevrilir.
function loginError(raw) {
  if (/did not approve|cancel|closed/i.test(raw)) return "Giriş tamamlanmadı. İstersen tekrar dene.";
  if (/could not be loaded|network/i.test(raw)) return "Giriş sayfası açılamadı. İnternet bağlantını kontrol edip tekrar dene.";
  return `Giriş başarısız: ${raw}`;
}

addEventListener("scroll", () => document.body.classList.toggle("scrolled", scrollY > 2), { passive: true });

$("login").onclick = () => run($("login"), async () => {
  const server = ($("server").value.trim() || DEFAULT_SERVER).replace(/\/+$/, "");
  state.server = server;
  await chrome.storage.local.set({ server });
  // Kick penceresi açılınca bu popup kapanabilir; oturum arka planda kaydedilir.
  const res = await chrome.runtime.sendMessage({ type: "login", server });
  if (!res.ok) throw new Error(res.friendly ? res.error : loginError(res.error));
});

$("logout").onclick = () => run($("logout"), async () => {
  await api("POST", "/auth/logout").catch(() => {});
  await chrome.storage.local.remove(["token", "teamId"]);
});

$("team").onchange = () => run(null, () => selectTeam(Number($("team").value)));
$("team-menu").onclick = () => {
  $("team-forms").hidden = !$("team-forms").hidden;
  $("team-menu").setAttribute("aria-expanded", String(!$("team-forms").hidden));
};

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
    const { id, name } = await api("POST", "/teams/join", { invite_code: form.invite_code.value.trim() });
    form.reset();
    await loadMe(id);
    showMessage(name ? `"${name}" ekibine katıldın.` : "Ekibe katıldın.", "info");
  });
};

// Tek kişilik kullanım: ad sormadan kullanıcının kendi listesi kurulur, sıradaki adım kanal eklemektir.
$("solo-start").onclick = () => run($("solo-start"), async () => {
  const { id } = await api("POST", "/teams", { name: `${state.me.user.name} ekibi` });
  await loadMe(id);
  showTab("crew");
  showMessage("Listen hazır. Moderatörü olduğun kanalları buradan ekle.", "info");
});

$("lend").onchange = () => run(null, async () => {
  const lend = $("lend").checked;
  try {
    if (lend && !(await ask(`Ekipteki moderatörler ${state.me.user.name} kanalında senin yayıncı yetkinle ban atabilecek. Açılsın mı?`))) return;
    await api("POST", `/teams/${state.teamId}/lend`, { lend });
    showMessage(lend ? "Yayıncı yetkin ekiple paylaşılıyor." : "Yayıncı yetkisi paylaşımı kapatıldı.", "info");
  } finally {
    await loadTeam();
  }
});

$("join-role").onchange = () => run(null, async () => {
  try {
    await api("POST", `/teams/${state.teamId}/settings`, { join_role: $("join-role").value });
    showMessage("Kaydedildi.", "info");
  } finally {
    await loadTeam();
  }
});

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

$("channel-self-add").onclick = () => run($("channel-self-add"), async () => {
  await api("POST", `/teams/${state.teamId}/channels`, { slug: state.me.user.name });
  await loadTeam();
  await loadBans();
});

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

$("team-delete").onclick = () => run($("team-delete"), async () => {
  const { name } = state.team;
  if (!(await ask(`"${name}" ekibi silinsin mi? Üyelikler, kanallar ve ortak liste kalıcı olarak silinir; bu geri alınamaz. Kick'teki banlar yerinde kalır.`))) return;
  await api("DELETE", `/teams/${state.teamId}`);
  await forgetTeam();
  showMessage(`"${name}" ekibi silindi.`, "info");
});

// Seçili ekip artık yok ya da erişilemez: kalan ekiplerden biri açılır.
async function forgetTeam() {
  clearTimeout(queueTimer);
  state.teamId = null;
  state.team = null;
  await chrome.storage.local.remove("teamId");
  await loadMe(null);
}

$("team-leave").onclick = () => run($("team-leave"), async () => {
  const { name } = state.team;
  if (!(await ask(`"${name}" ekibinden ayrılmak istiyor musun? Yeniden katılmak için davet kodu gerekir.`))) return;
  await api("POST", `/teams/${state.teamId}/leave`);
  await forgetTeam();
  showMessage(`"${name}" ekibinden ayrıldın.`, "info");
});

$("account-delete").onclick = () => run($("account-delete"), async () => {
  if (!(await ask("Hesabın silinsin mi? Oturumların, üyeliklerin ve yalnızca senin olduğun ekipler kalıcı olarak silinir; Kick'e verdiğin erişim geri alınır. Başka ekiplerin listesindeki banların kalır ama adın görünmez. Kick'teki banlar etkilenmez."))) return;
  await api("DELETE", "/me");
  clearTimeout(queueTimer);
  state.token = null;
  state.teamId = null;
  await chrome.storage.local.remove(["token", "teamId"]);
  await render();
  showMessage("Hesabın silindi.", "info");
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

// Sebep alanı bir hazır sebeple aynıysa o etiket seçili görünür.
function syncPresets() {
  const reason = $("reason").value.trim();
  for (const preset of $("reason-presets").children) {
    const active = preset.textContent === reason;
    preset.classList.toggle("active", active);
    preset.setAttribute("aria-pressed", String(active));
  }
}

for (const preset of $("reason-presets").children) {
  preset.onclick = () => {
    $("reason").value = preset.classList.contains("active") ? "" : preset.textContent;
    syncPresets();
  };
}
$("reason").oninput = syncPresets;
syncPresets();

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
      syncPresets();
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
    if (!failed.length) {
      form.reason.value = "";
      syncPresets();
    } else {
      showMessage(`${failed.length} kullanıcı banlanamadı; adlar alanda bırakıldı.`);
    }
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
