const $ = (id) => document.getElementById(id);
const MAX_IMPORT = 6000;
// Bundan uzun listeler sunucudaki sıraya gider; panel kapansa da işlenmeye devam eder.
const QUEUE_THRESHOLD = 10;

// Ekip içi roller, yetkiye göre sıralı (sunucudaki ROLES ile aynı).
const ROLE_RANK = { viewer: 0, mod: 1, admin: 2, owner: 3 };
const ROLE_KEY = { owner: "roleOwner", admin: "roleAdmin", mod: "roleMod", viewer: "roleViewer" };
const roleLabel = (role) => t(ROLE_KEY[role]);
// Rol bilgisi göndermeyen eski sunucularda sahip dışındaki herkes moderatör sayılır.
const roleOf = (item) => item.role || (item.owner ? "owner" : "mod");
const can = (need) => ROLE_RANK[roleOf(state.team)] >= ROLE_RANK[need];

let state = {
  server: DEFAULT_SERVER, token: null, teamId: null, me: null, team: null, view: "list",
  list: { bans: [], matched: 0, active_total: 0 },
  // Ban formundaki kanal seçimi: all (ekibin bütün kanalları) | own (yalnızca kendi kanalım) | custom (işaretlenenler)
  scope: { mode: "all", ids: [] }, scopeSupported: false, unbanScopeSupported: false,
};

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
  // Token taşıyan her istek buradan geçer; şifresiz uzak sunucuya hiçbir koşulda gitmez.
  const problem = serverUrlProblem(state.server);
  if (problem) throw new Error(problem);
  let res;
  try {
    res = await fetch(state.server + path, {
      method,
      headers: {
        Authorization: `Bearer ${state.token}`,
        // Sunucu hata mesajlarını bu dilde döndürür (eski sunucular yok sayar).
        "Accept-Language": LANG,
        ...(body ? { "Content-Type": "application/json" } : {}),
      },
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    // Tarayıcının "Failed to fetch" hatası kullanıcıya bir şey söylemez.
    throw new Error(t("netDown"));
  }
  const data = await res.json().catch(() => ({}));
  if (res.status === 401) {
    await chrome.storage.local.remove("token");
    state.token = null;
    render();
  }
  if (!res.ok) throw Object.assign(new Error(data.error || t("serverDown", res.status)), { status: res.status });
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
// Onay düğmesi varsayılan olarak kırmızıdır; geri alınabilir işlemlerde (safe) normal renkte olur.
function ask(text, { yes = t("confirm"), safe = false } = {}) {
  return new Promise((resolve) => {
    const dialog = $("confirm");
    const done = (answer) => { dialog.close(); resolve(answer); };
    $("confirm-text").textContent = text;
    $("confirm-yes").textContent = yes;
    $("confirm-yes").className = safe ? "primary" : "danger";
    $("confirm-yes").onclick = () => done(true);
    $("confirm-no").onclick = () => done(false);
    dialog.oncancel = () => resolve(false);
    dialog.showModal();
  });
}

function formatDuration(minutes) {
  if (!minutes) return t("permanent");
  if (minutes % 1440 === 0) return t("days", minutes / 1440);
  if (minutes % 60 === 0) return t("hours", minutes / 60);
  return t("minutes", minutes);
}

function formatDate(seconds) {
  return new Date(seconds * 1000).toLocaleString(localeTag(), {
    day: "numeric", month: "long", year: "numeric", hour: "2-digit", minute: "2-digit",
  });
}

// "3 dk önce" gibi göreli zaman; bir haftadan eskiler kısa tarihle gösterilir.
function formatAgo(seconds) {
  const diff = Math.max(0, Date.now() / 1000 - seconds);
  if (diff < 45) return t("justNow");
  if (diff < 3600) return t("minAgo", Math.max(1, Math.round(diff / 60)));
  if (diff < 86400) return t("hourAgo", Math.round(diff / 3600));
  if (diff < 7 * 86400) return t("dayAgo", Math.round(diff / 86400));
  const date = new Date(seconds * 1000);
  const sameYear = date.getFullYear() === new Date().getFullYear();
  return date.toLocaleDateString(localeTag(), { day: "numeric", month: "short", ...(sameYear ? {} : { year: "numeric" }) });
}

function timeEl(seconds) {
  const node = el("time", { dateTime: new Date(seconds * 1000).toISOString(), title: formatDate(seconds), textContent: formatAgo(seconds) });
  node.dataset.ts = seconds;
  return node;
}

// Süreli uzaklaştırmanın bitişi; eski sunucu expires_at göndermezse banın atıldığı andan hesaplanır.
function banExpiry(ban) {
  if (!ban.duration) return null;
  return ban.expires_at ?? ban.created_at + ban.duration * 60;
}

// "45 dk kaldı" gibi kalan süre.
function formatLeft(seconds) {
  const minutes = Math.max(1, Math.ceil((seconds - Date.now() / 1000) / 60));
  if (minutes < 60) return t("minLeft", minutes);
  if (minutes < 1440) return t("hourLeft", Math.round(minutes / 60));
  return t("dayLeft", Math.round(minutes / 1440));
}

// Süreli banın etiketi: süre dolunca "Ceza bitti" olur ve kart sönükleşir.
function updateTimedTag(tag) {
  const expires = Number(tag.dataset.expires);
  const ended = Date.now() / 1000 >= expires;
  const card = tag.closest(".ban");
  tag.className = `tag ${ended ? "ended" : "timed"}`;
  tag.textContent = ended ? t("ended") : formatDuration(Number(tag.dataset.duration));
  tag.title = ended
    ? t("endedTitle", formatDuration(Number(tag.dataset.duration)), formatDate(expires))
    : t("leftTitle", formatLeft(expires), formatDate(expires));
  if (card) {
    card.classList.toggle("ended", ended);
    // Süresi dolan uzaklaştırmada "Tekrar dene" kullanıcıyı baştan uzaklaştırır, "Kaldır" da boşa gider.
    card.querySelector(".actions")?.toggleAttribute("hidden", ended);
  }
}

// Panel açık kaldıkça göreli zamanlar ve süreli ban etiketleri eskimesin.
setInterval(() => {
  for (const node of document.querySelectorAll("time[data-ts]")) node.textContent = formatAgo(Number(node.dataset.ts));
  for (const tag of document.querySelectorAll(".tag[data-expires]")) updateTimedTag(tag);
}, 30000);

const STATUS_KEY = {
  ok: "statusOk",
  failed: "statusFailed",
  pending: "statusPending",
  unbanned: "statusUnbanned",
  unban_failed: "statusUnbanFailed",
};

// Ban Kick'e birkaç saniyede uygulanır; kanal sonucu ancak o bitince yazılır. Bu arada alınan liste
// (art arda atılan banlarda, başka bir pencereden ya da başka bir moddan) banı "henüz uygulanmadı" gösterir.
// Yeni atılmış böyle bir ban "uygulanıyor" sayılır: Tekrar dene düğmesi çıkmaz, liste kendini yeniler.
const APPLYING_SECONDS = 90;

function applying(ban) {
  if (ban.revoked_at || !ban.results.some((r) => r.status === "pending")) return false;
  const now = Date.now() / 1000 + (state.list.clockSkew || 0);
  return now - ban.created_at < APPLYING_SECONDS;
}

function banCard(ban) {
  // Kısmen kaldırılmış aktif banda, kaldırılan kanallar eksik sayılmaz: orada ban bilerek yok.
  const live = ban.revoked_at ? ban.results : ban.results.filter((r) => r.status !== "unbanned");
  const applied = live.filter((r) => r.status === "ok").length;
  const complete = applied === live.length;
  const inFlight = applying(ban);
  // Banın atılmasından sonra eklenen kanalda ban hiç denenmemiştir ("uygulanmadı"). Bu bir hata değildir;
  // kartta açıkça yazılır ve düğme "Tekrar dene" yerine ne yapacağını söyler.
  const missing = inFlight || ban.revoked_at ? [] : ban.results.filter((r) => r.status === "pending").map((r) => r.slug);
  const failed = ban.revoked_at ? [] : ban.results.filter((r) => r.status === "failed");
  const hasFailed = failed.length > 0;
  const chips = ban.results.map((r) => {
    const via = r.via === "broadcaster" && r.status === "ok" ? t("viaBroadcaster") : "";
    const status = inFlight && r.status === "pending" ? t("statusApplying") : t(STATUS_KEY[r.status]);
    return el("span", {
      className: `chip ${r.status}${inFlight && r.status === "pending" ? " applying" : ""}`,
      title: `${status}${via}${r.detail ? ` — ${r.detail}` : ""}`,
      textContent: r.slug,
    });
  });
  const tag = ban.revoked_at
    ? el("span", { className: "tag off", textContent: t("revoked") })
    : el("span", { className: `tag ${ban.duration ? "timed" : "perm"}`, textContent: formatDuration(ban.duration) });
  if (!ban.revoked_at && ban.duration) {
    tag.dataset.expires = banExpiry(ban);
    tag.dataset.duration = ban.duration;
  }

  // Kick'te elle atılmış banın kaydı, adıyla kaldırılırken açılır; kaydı açan kişi banı kaldırandır.
  const reason = ban.external ? t("externalReason") : ban.reason || t("noReason");
  const card = el("div", { className: `ban${ban.revoked_at ? " revoked" : complete || inFlight ? "" : " partial"}` },
    el("div", { className: "head" }, el("span", { className: "name", textContent: ban.target_name }), tag),
    el("div", { className: `reason${ban.reason ? "" : " none"}`, textContent: reason }),
    el("div", { className: "meta" },
      el("span", { className: "avatar mini", textContent: ban.created_by.slice(0, 1).toUpperCase() }),
      el("span", { className: "who", textContent: ban.external ? t("externalWho", ban.created_by) : ban.created_by }),
      "·",
      timeEl(ban.created_at))
  );
  const foot = el("div", { className: "foot" }, el("div", { className: "chips" }, ...chips));
  // Moderatör yalnızca kendi attığı banı kaldırabilir; başkasınınkini sahip ve yöneticiler kaldırır.
  const mine = ban.created_by_id === undefined || ban.created_by_id === state.me.user.id;
  if (!ban.revoked_at && can("mod")) {
    const actions = el("div", { className: "actions" });
    if (!complete && !inFlight) {
      const retry = el("button", {
        className: "ghost small retry",
        textContent: missing.length && !hasFailed ? t("applyMissing") : t("retry"),
      });
      retry.onclick = () => run(retry, async () => {
        await api("POST", `/teams/${state.teamId}/bans/${ban.id}/retry`);
        await loadBans();
      });
      actions.append(retry);
    }
    if (mine || can("admin")) {
      const revoke = el("button", { className: "ghost small", textContent: t("unban") });
      revoke.onclick = () => run(revoke, async () => {
        if (!(await ask(t("confirmRevoke", ban.target_name)))) return;
        await api("DELETE", `/teams/${state.teamId}/bans/${ban.id}`);
        await loadBans();
      });
      actions.append(revoke);
    }
    if (actions.children.length) foot.append(actions);
  }
  card.append(foot);
  if (missing.length) card.append(el("div", { className: "hint", textContent: t("missingChannels", missing.join(", "), missing.length) }));
  // Kick'in verdiği sebep (ör. o kanalda moderatör olmamak) imleç üstüne gelmeden de görünür; ilk ikisi yazılır.
  const reasons = failed.filter((r) => r.detail);
  if (reasons.length) {
    const shown = reasons.slice(0, 2).map((r) => `${r.slug}: ${r.detail}`).join(" · ");
    card.append(el("div", { className: "hint bad", textContent: shown + (reasons.length > 2 ? ` · +${reasons.length - 2}` : "") }));
  }
  if (tag.dataset.expires) updateTimedTag(tag);
  return card;
}

// Liste: kalıcı banlar ve süren uzaklaştırmalar. Geçmiş: kaldırılanlar ve süresi dolan uzaklaştırmalar.
function isActive(ban) {
  if (ban.revoked_at) return false;
  return !ban.duration || banExpiry(ban) > Date.now() / 1000;
}

function renderBans() {
  const { matched, active_total: activeTotal } = state.list;
  const history = state.view === "history";
  // 0.7.1 ve öncesindeki sunucu görünümü ayırmaz; ayrım burada da yapılır.
  const bans = state.list.bans.filter((ban) => isActive(ban) !== history);
  $("list-count").textContent = activeTotal;
  $("list-count").hidden = !activeTotal;
  fitTabs();
  $("ban-list").classList.toggle("history", history);
  // Geçmişi ekibin herkesi için siler; yalnızca sahip ve yöneticiler, silinecek bir şey varken görür.
  // Bir kanalda kaldırılamamış kayıt silinmez (sunucu da bırakır), silinebilir sayılmaz.
  const deletable = bans.some((ban) => !(ban.results || []).some((r) => r.status === "unban_failed"));
  $("history-clear").hidden = !(history && can("admin") && deletable);
  // Dışa aktarma aramadan bağımsız olarak ekibin bütün kalıcı banlarını indirir; ekibin her üyesi kullanabilir.
  $("list-export").hidden = history || !activeTotal;

  const searching = $("list-search").value.trim();
  const empty = searching
    ? emptyState("search", t("noMatchTitle"), t("noMatchHint"))
    : history
      ? emptyState("history", t("historyEmptyTitle"), t("historyEmptyHint"))
      : emptyState("shield", t("noActiveTitle"), t("noActiveHint"));
  const cards = bans.length ? bans.map(banCard) : [empty];
  // Sunucu en fazla 200 kayıt döndürür; matched, bu görünümdeki toplam kayıttır.
  if (matched > state.list.bans.length) {
    cards.push(el("p", {
      className: "muted small",
      textContent: t("moreRecords", matched, state.list.bans.length),
    }));
  }
  $("ban-list").replaceChildren(...cards);
}

// Her liste isteği bir sıra numarası alır; arama yazılırken geç gelen eski yanıt yenisinin üstüne yazmasın.
let loadSeq = 0;

async function loadBans() {
  const seq = ++loadSeq;
  const params = new URLSearchParams();
  const query = $("list-search").value.trim();
  if (query) params.set("q", query);
  const view = state.view;
  // Eski sunucu view'ı tanımaz; revoked=1 ile hepsini döndürür, ayrımı renderBans yapar.
  if (view === "history") params.set("view", "history"), params.set("revoked", "1");
  const teamId = state.teamId;
  // Ekibin listesi ilk kez gelirken iskelet; sonraki yenilemelerde eldeki kartlar yerinde kalır.
  if (!state.listLoaded) $("ban-list").replaceChildren(...[0, 1, 2].map(skeletonCard));
  let list;
  try {
    list = await api("GET", `/teams/${teamId}/bans?${params}`);
  } catch (e) {
    if (seq === loadSeq && teamId === state.teamId && view === state.view && !state.listLoaded) {
      $("ban-list").replaceChildren(emptyState("alert", t("listFailedTitle"), t("listFailedHint")));
    }
    throw e;
  }
  if (seq !== loadSeq || teamId !== state.teamId || view !== state.view) return;
  // Eski sunucu saatini göndermez; o zaman panelin saati kullanılır.
  list.clockSkew = typeof list.now === "number" ? list.now - Date.now() / 1000 : 0;
  state.list = list;
  state.listLoaded = true;
  renderBans();
  // Kick'e gitmekte olan ban varken liste birkaç saniyede bir yenilenir; bitince durur.
  clearTimeout(applyingTimer);
  if (list.bans.some(applying)) {
    applyingTimer = setTimeout(() => loadBans().catch(() => {}), APPLYING_REFRESH_MS);
  }
}

const APPLYING_REFRESH_MS = 2500;
let applyingTimer = null;

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
  $("scope-field").hidden = true;
  if (slugs.length) {
    renderScope();
  } else if (admin) {
    const add = el("button", { type: "button", className: "link", textContent: t("addChannel") });
    add.onclick = () => {
      showTab("crew");
      $("channel-add").elements.slug.focus();
    };
    $("targets").replaceChildren(t("noChannelsYet"), add);
  } else {
    $("targets").textContent = t("noChannelsAdmins");
  }
  syncMode();
  $("ban-submit").disabled = !slugs.length;

  $("channel-add").hidden = !admin;
  $("channel-count").textContent = team.channels.length;
  $("member-count").textContent = team.members.length;

  // Kick'te kanal kimliği kullanıcı kimliğiyle aynı; kendi kanalı listede yoksa tek tıkla eklenebilsin.
  const own = team.channels.find((c) => c.broadcaster_id === me.id);
  $("channel-self").hidden = !admin || Boolean(own);
  $("channel-self-text").textContent = t("ownChannelMissing", me.name);

  // Yetki paylaşımı yalnızca kanalı bu ekibin listesinde olan üyeye sorulur; kararı yalnızca o verir.
  $("lend-card").hidden = !own || team.lend === undefined;
  $("lend").checked = Boolean(team.lend);

  $("invite-card").hidden = !admin;
  $("invite").textContent = team.invite_code;
  $("copy-invite-link").hidden = !(state.inviteLinks?.server === state.server && state.inviteLinks.ok);
  $("invite-text").textContent = team.join_role === "viewer"
    ? t("inviteViewerText")
    : t("inviteModText");
  $("join-role-row").hidden = !owner || team.join_role === undefined;
  $("join-role").value = team.join_role || "mod";
  $("team-leave-card").hidden = owner || team.role === undefined;
  $("team-danger").hidden = !owner;

  $("channels").replaceChildren(...team.channels.map((c) => {
    const item = el("li", {}, el("span", { className: "grow mono", textContent: c.slug }));
    if (c.broadcaster_joined) {
      item.append(el("span", {
        className: "tag off",
        textContent: t("broadcasterOn"),
        title: t("broadcasterOnTitle"),
      }));
    } else if (c.broadcaster_member) {
      item.append(el("span", {
        className: "tag off",
        textContent: t("broadcasterMember"),
        title: t("broadcasterMemberTitle"),
      }));
    }
    if (admin) {
      const remove = el("button", { className: "ghost small", textContent: t("removeChannel") });
      remove.onclick = () => run(remove, async () => {
        if (!(await ask(t("confirmChannelRemove", c.slug)))) return;
        await api("DELETE", `/teams/${team.id}/channels/${c.broadcaster_id}`);
        await loadTeam();
        await loadBans();
      });
      item.append(remove);
    }
    return item;
  }));
  if (!team.channels.length) {
    $("channels").append(emptyState("channel", t("noChannelsTitle"),
      admin ? t("noChannelsHintAdmin") : t("noChannelsHint"), "li"));
  }

  $("members").replaceChildren(...team.members.map((m) => {
    const role = roleOf(m);
    const item = el("li", {},
      el("span", { className: "avatar", textContent: m.name.slice(0, 1).toUpperCase() }),
      el("span", { className: "grow" }, m.name, m.id === me.id ? el("span", { className: "you", textContent: t("you") }) : "")
    );
    if (owner && role !== "owner" && team.role !== undefined) {
      // Sahip, diğer üyelerin rolünü buradan değiştirir; son seçenek sahipliği devreder.
      const select = el("select", { className: "small", ariaLabel: t("roleFor", m.name) },
        ...["admin", "mod", "viewer"].map((r) => el("option", { value: r, textContent: roleLabel(r), selected: r === role })),
        el("option", { value: "owner", textContent: t("transferOwnership") }));
      select.onchange = () => run(null, async () => {
        const next = select.value;
        try {
          if (next === "owner" && !(await ask(t("confirmTransfer", m.name)))) return;
          await api("POST", `/teams/${team.id}/members/${m.id}/role`, { role: next });
          showMessage(next === "owner" ? t("transferred", m.name) : t("roleChanged", m.name, roleLabel(next)), "info");
        } finally {
          await loadTeam();   // vazgeçilirse ya da hata olursa seçim eski haline döner
        }
      });
      item.append(select);
    } else {
      item.append(el("span", { className: "tag off", textContent: roleLabel(role) }));
    }
    if (admin && m.id !== me.id && ROLE_RANK[role] < ROLE_RANK[roleOf(team)]) {
      const remove = el("button", { className: "ghost small", textContent: t("removeMember") });
      remove.onclick = () => run(remove, async () => {
        if (!(await ask(t("confirmRemoveMember", m.name)))) return;
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

// Liste ve Geçmiş aynı paneli (arama + kartlar) paylaşır.
const PANEL_OF = { history: "list" };

function showTab(name) {
  const panel = PANEL_OF[name] || name;
  for (const button of document.querySelectorAll(".tabs button")) {
    button.classList.toggle("active", button.dataset.tab === name);
    const own = PANEL_OF[button.dataset.tab] || button.dataset.tab;
    $(`tab-${own}`).hidden = own !== panel;
  }
  if (panel !== "list") return;
  if (state.view !== name) {
    state.view = name;
    state.listLoaded = false;
  }
  run(null, loadBans);
}

// teamRequest: açılışta /me ile birlikte gönderilmiş ekip isteği; varsa yanıtı ikinci kez beklenmez.
async function selectTeam(teamId, teamRequest) {
  state.teamId = teamId;
  state.listLoaded = false;
  await chrome.storage.local.set({ teamId });
  $("team").value = String(teamId);
  $("team-view").hidden = false;
  $("ban-result").replaceChildren();
  const team = teamRequest && await teamRequest;
  if (team) {
    state.team = team;
    renderTeam();
  } else {
    await loadTeam();
  }
  // Liste ve sıra paneli bekletmez; ikisi birlikte istenir, liste gelene dek iskeleti görünür.
  Promise.all([loadBans(), pollQueue()]).catch((e) => showMessage(e.message));
}

const PROBLEM_KEY = {
  notfound: "problemNotfound",
  rejected: "problemRejected",
  partial: "problemPartial",
  unban_partial: "problemPartial",
  error: "problemError",
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
  const banned = (counts.done || 0) + (counts.partial || 0);
  const unbanned = (counts.unbanned || 0) + (counts.unban_partial || 0);
  const parts = banned || !unbanned ? [t("queueBanned", banned)] : [];
  if (unbanned) parts.push(t("queueUnbanned", unbanned));
  if (counts.notfound) parts.push(t("queueNotfound", counts.notfound));
  if (counts.rejected) parts.push(t("queueRejected", counts.rejected));
  if (counts.error) parts.push(t("queueErrors", counts.error));
  $("queue-summary").textContent = (pending ? t("queuePending", pending) : t("queueDone")) + parts.join(" · ");

  $("queue-problems").hidden = !queueProblems.length;
  $("queue-problems").querySelector("summary").textContent = t("queueProblems", queueProblems.length);
  $("queue-problem-list").replaceChildren(...queueProblems.map((p) => el("li", {},
    el("span", { className: "grow mono", textContent: p.name }),
    el("span", { className: "muted", textContent: p.detail || t(PROBLEM_KEY[p.status]), title: p.detail })
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
  if (!(await ask(t("confirmQueueCancel")))) return;
  await api("DELETE", `/teams/${state.teamId}/imports/pending`);
  await pollQueue();
});

$("queue-clear").onclick = () => run($("queue-clear"), async () => {
  await api("DELETE", `/teams/${state.teamId}/imports/finished`);
  await pollQueue();
});

$("history-clear").onclick = () => run($("history-clear"), async () => {
  if (!(await ask(t("confirmHistoryClear")))) return;
  let res;
  try {
    res = await api("DELETE", `/teams/${state.teamId}/bans/history`);
  } catch (e) {
    // 0.10.0 öncesi sunucu bu yolu tanımaz; yalın "Bulunamadı" kullanıcıya bir şey söylemez.
    if (e.status === 404 && state.token) throw new Error(t("oldServerHistory"));
    throw e;
  }
  showMessage(t("historyCleared", res.deleted, res.kept), "info");
  await loadBans();
});

// Dosyadan yükle ile aynı biçim: her satırda bir kullanıcı adı. Liste 200 kayıtla sınırlı, bu yüzden sunucudan ayrı alınır.
$("list-export").onclick = () => run($("list-export"), async () => {
  let res;
  try {
    res = await api("GET", `/teams/${state.teamId}/bans/export`);
  } catch (e) {
    // 0.11.0 öncesi sunucu bu yolu tanımaz.
    if (e.status === 404 && state.token) throw new Error(t("oldServerExport"));
    throw e;
  }
  if (!res.names.length) return showMessage(t("exportEmpty"), "info");
  const team = (state.me.teams.find((x) => x.id === state.teamId) || {}).name || "ekip";
  const slug = team.normalize("NFKD").replace(/[^\w-]+/g, "-").replace(/^-+|-+$/g, "").toLowerCase() || "ekip";
  const now = new Date();
  const date = [now.getFullYear(), now.getMonth() + 1, now.getDate()].map((n) => String(n).padStart(2, "0")).join("-");
  const url = URL.createObjectURL(new Blob([res.names.join("\n") + "\n"], { type: "text/plain;charset=utf-8" }));
  const link = el("a", { href: url, download: `magnetosphere-${slug}-${date}.txt` });
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  showMessage(t("exported", res.names.length), "info");
});

$("queue-copy").onclick = async () => {
  const names = queueProblems.filter((p) => p.status === "notfound").map((p) => p.name);
  await navigator.clipboard.writeText(names.join("\n"));
  showMessage(t("namesCopied", names.length), "info");
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
  showMessage(t("fileLoaded", files.map((f) => f.name).join(", "), added), "info");
});

async function loadMe(preferredTeamId, teamRequest) {
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
  $("welcome-title").textContent = t("welcome", state.me.user.name);
  $("welcome-text").textContent = canCreate
    ? t("welcomeSolo")
    : t("welcomeInvite");
  if (teams.length) {
    const wanted = teams.find((t) => t.id === preferredTeamId) || teams[0];
    await selectTeam(wanted.id, wanted.id === preferredTeamId ? teamRequest : null);
  }
}

async function render() {
  const loggedIn = Boolean(state.token);
  $("login-view").hidden = loggedIn;
  $("app-view").hidden = !loggedIn;
  $("user").hidden = !loggedIn;
  $("account-card").hidden = !loggedIn;
  $("server").value = state.server;
  if (!loggedIn) return handlePendingInvite();
  // Sunucu yanıt verene dek boş panel yerine iskelet görünür.
  showMessage("");
  $("app-view").classList.remove("failed");
  $("app-view").classList.add("loading");
  // Son seçilen ekip /me ile aynı anda istenir; panel iki yanıtı art arda beklemez.
  // Kullanıcı o ekipten çıkmışsa yanıt boş sayılır ve ekip /me'den sonra yeniden seçilir.
  const teamRequest = state.teamId ? api("GET", `/teams/${state.teamId}`).catch(() => null) : null;
  try {
    await loadMe(state.teamId, teamRequest);
  } catch (e) {
    // Oturum düştüyse giriş ekranı zaten açılmıştır; diğer durumda yarım panel yerine tekrar deneme sunulur.
    if (state.token) {
      $("load-error-text").textContent = e.message;
      $("app-view").classList.add("failed");
    }
  }
  $("load-error").hidden = !$("app-view").classList.contains("failed");
  $("app-view").classList.remove("loading");
  if ($("app-view").classList.contains("failed")) return;
  if (state.inviteLinks?.server !== state.server) checkInviteLinks();
  checkScopeSupport();
  await handlePendingInvite();
}

$("load-retry").onclick = () => render();

// Chrome'un ham giriş hataları kullanıcının anlayacağı bir mesaja çevrilir.
function loginError(raw) {
  if (/did not approve|cancel|closed/i.test(raw)) return t("loginCancelled");
  if (/could not be loaded|network/i.test(raw)) return t("loginPageFailed");
  return t("loginFailed", raw);
}

addEventListener("scroll", () => document.body.classList.toggle("scrolled", scrollY > 2), { passive: true });

$("login").onclick = () => run($("login"), async () => {
  const server = ($("server").value.trim() || DEFAULT_SERVER).replace(/\/+$/, "");
  const problem = serverUrlProblem(server);
  if (problem) throw new Error(problem);
  state.server = server;
  await chrome.storage.local.set({ server });
  // Kick penceresi açılınca bu popup kapanabilir; oturum arka planda kaydedilir.
  const res = await chrome.runtime.sendMessage({ type: "login", server });
  if (!res.ok) throw new Error(res.friendly ? res.error : loginError(res.error));
});

$("logout").onclick = () => run($("logout"), async () => {
  await api("POST", "/auth/logout").catch(() => {});
  await chrome.storage.local.remove(["token", "teamId"]);
  await clearDraft();
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
    showMessage(name ? t("joined", name) : t("joinedPlain"), "info");
  });
};

// Tek kişilik kullanım: ad sormadan kullanıcının kendi listesi kurulur, sıradaki adım kanal eklemektir.
$("solo-start").onclick = () => run($("solo-start"), async () => {
  const { id } = await api("POST", "/teams", { name: t("soloTeamName", state.me.user.name) });
  await loadMe(id);
  showTab("crew");
  showMessage(t("soloReady"), "info");
});

$("lend").onchange = () => run(null, async () => {
  const lend = $("lend").checked;
  try {
    if (lend && !(await ask(t("confirmLend", state.me.user.name)))) return;
    await api("POST", `/teams/${state.teamId}/lend`, { lend });
    showMessage(lend ? t("lendOn") : t("lendOff"), "info");
  } finally {
    await loadTeam();
  }
});

$("join-role").onchange = () => run(null, async () => {
  try {
    await api("POST", `/teams/${state.teamId}/settings`, { join_role: $("join-role").value });
    showMessage(t("saved"), "info");
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
  showMessage(t("inviteCopied"), "info");
};

// Kod bağlantının # kısmında durur: tarayıcı onu sunucuya göndermez, sayfa kodu eklentiye kendisi verir.
$("copy-invite-link").onclick = async () => {
  await navigator.clipboard.writeText(`${state.server}/join#${$("invite").textContent}`);
  showMessage(t("inviteLinkCopied"), "info");
};

// Davet bağlantısı yalnızca davet sayfası olan (0.12.0+) ve eklentinin mesajını kabul ettiği sunucuda çalışır.
// Kendi sunucusunu kuranlar alan adını manifest'e eklemediyse düğme görünmez, kod yine kopyalanabilir.
async function checkInviteLinks() {
  const server = state.server;
  const matches = chrome.runtime.getManifest().externally_connectable?.matches || [];
  let ok = false;
  if (matches.some((m) => m.replace(/\/\*$/, "") === server)) {
    try {
      const { version = "0" } = await api("GET", "/health");
      const [major, minor] = version.split(".").map(Number);
      ok = major > 0 || minor >= 12;
    } catch {}
  }
  if (server !== state.server) return;
  state.inviteLinks = { server, ok };
  $("copy-invite-link").hidden = !ok;
}

// Davet sayfasından gelen kod: kişi ekibin adını ve sahibini görüp onaylarsa katılır.
// Kayıt ancak bir cevap alınınca silinir; onay açıkken panel kapanırsa davet bir sonraki açılışta yeniden sorulur.
const INVITE_TTL = 24 * 3600 * 1000;
let inviteBusy = false;

async function handlePendingInvite() {
  if (inviteBusy) return;
  inviteBusy = true;
  try {
    const { pendingInvite: invite } = await chrome.storage.local.get("pendingInvite");
    if (!invite) return;
    const drop = () => chrome.storage.local.remove("pendingInvite");
    if (Date.now() - invite.at > INVITE_TTL) return await drop();
    if (!state.token) return showMessage(t("inviteLoginFirst"), "info");
    // Davet saklı kalır: kişi sunucu adresini değiştirip giriş yapınca yeniden sorulur.
    if (invite.server !== state.server) return showMessage(t("inviteOtherServer", invite.server));
    await run(null, async () => {
      let team;
      try {
        team = await api("POST", "/teams/join/preview", { invite_code: invite.code });
      } catch (e) {
        // Geçersiz ya da yenilenmiş kod atılır; ağ hatasında davet sonraki açılışa kalır.
        if (e.status === 400 || e.status === 404) await drop();
        throw e;
      }
      if (team.member) {
        await drop();
        await loadMe(team.id);
        return showMessage(t("inviteAlreadyMember", team.name), "info");
      }
      const yes = await ask(t("confirmInviteJoin", team.name, team.owner || "?", roleLabel(team.join_role).toLocaleLowerCase(localeTag())),
                            { yes: t("join"), safe: true });
      await drop();
      if (!yes) return;
      const { id, name, already } = await api("POST", "/teams/join", { invite_code: invite.code });
      await loadMe(id);
      showMessage(already ? t("inviteAlreadyMember", name) : t("joined", name), "info");
    });
  } finally {
    inviteBusy = false;
  }
}

$("rotate-invite").onclick = () => run($("rotate-invite"), async () => {
  if (!(await ask(t("confirmRotate")))) return;
  await api("POST", `/teams/${state.teamId}/invite`);
  await loadTeam();
  showMessage(t("rotated"), "info");
});

$("team-delete").onclick = () => run($("team-delete"), async () => {
  const { name } = state.team;
  if (!(await ask(t("confirmTeamDelete", name)))) return;
  await api("DELETE", `/teams/${state.teamId}`);
  await forgetTeam();
  showMessage(t("teamDeleted", name), "info");
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
  if (!(await ask(t("confirmLeave", name)))) return;
  await api("POST", `/teams/${state.teamId}/leave`);
  await forgetTeam();
  showMessage(t("left", name), "info");
});

$("account-delete").onclick = () => run($("account-delete"), async () => {
  if (!(await ask(t("confirmAccountDelete")))) return;
  await api("DELETE", "/me");
  clearTimeout(queueTimer);
  state.token = null;
  state.teamId = null;
  await chrome.storage.local.remove(["token", "teamId"]);
  await clearDraft();
  toggleSettings(false);
  await render();
  showMessage(t("accountDeleted"), "info");
});

let searchTimer = null;
$("list-search").oninput = () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => run(null, loadBans), 250);
};

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

// Panel, Chrome'da başka bir yere tıklanınca kapanır ve içindeki her şey silinir. Ban formu bu yüzden her
// değişiklikte saklanır, açılışta geri yüklenir. Ban atılıp alan boşalınca taslak da boşalır.
const DRAFT_KEY = "banDraft";
let draftReady = false;

function saveDraft() {
  if (!draftReady) return;
  const form = $("tab-ban");
  const draft = { username: form.username.value, reason: form.reason.value,
                  duration: form.duration.value, mode: form.mode.value, scope: state.scope };
  if (!draft.username.trim() && !draft.reason.trim() && !draft.duration && draft.mode === "ban"
      && state.scope.mode === "all") {
    chrome.storage.local.remove(DRAFT_KEY);
  } else {
    chrome.storage.local.set({ [DRAFT_KEY]: draft });
  }
}

// Sağ tık menüsünden gelen ad taslaktaki adların sonuna eklenir; önceki yazılanlar kaybolmaz.
async function restoreDraft(extraName) {
  const { [DRAFT_KEY]: draft } = await chrome.storage.local.get(DRAFT_KEY);
  const form = $("tab-ban");
  if (draft) {
    form.username.value = draft.username || "";
    form.reason.value = draft.reason || "";
    for (const radio of form.duration) radio.checked = radio.value === (draft.duration || "");
    for (const radio of form.mode) radio.checked = radio.value === (draft.mode || "ban");
    const saved = draft.scope || {};
    state.scope = {
      mode: saved.mode === "own" || saved.mode === "custom" ? saved.mode : "all",
      ids: Array.isArray(saved.ids) ? saved.ids.filter(Number.isInteger) : [],
    };
  }
  if (extraName) form.username.value = parseUsernames(`${form.username.value}\n${extraName}`).join("\n");
  draftReady = true;
  updateNameCount();
  syncPresets();
  syncMode();
  if (state.team) renderScope();
}

// Çıkışta yarım kalan form da silinir; aynı bilgisayarda başka hesapla giren görmesin.
async function clearDraft() {
  draftReady = false;
  $("tab-ban").reset();
  state.scope = { mode: "all", ids: [] };
  await chrome.storage.local.remove(DRAFT_KEY);
  await restoreDraft("");
}

function updateNameCount() {
  const count = parseUsernames($("username").value).length;
  $("name-count").textContent = t("userCount", count);
  $("name-count").hidden = count < 2;
  saveDraft();
}

$("username").oninput = updateNameCount;
for (const radio of $("tab-ban").elements.duration) radio.onchange = saveDraft;

// Sebep alanı bir hazır sebeple aynıysa o etiket seçili görünür.
function syncPresets() {
  const reason = $("reason").value.trim();
  for (const preset of $("reason-presets").children) {
    const active = preset.textContent === reason;
    preset.classList.toggle("active", active);
    preset.setAttribute("aria-pressed", String(active));
  }
  saveDraft();
}

for (const preset of $("reason-presets").children) {
  preset.onclick = () => {
    $("reason").value = preset.classList.contains("active") ? "" : preset.textContent;
    syncPresets();
  };
}
$("reason").oninput = syncPresets;
syncPresets();

const unbanMode = () => $("tab-ban").elements.mode.value === "unban";

// Ban kaldırmada sebep ve süre yoktur; düğme yapılacak işi söyler.
function syncMode() {
  const unban = unbanMode();
  // Düğme, işlemin uygulanacağı kanal sayısını söyler.
  const count = state.team ? resolveScope().list.length : 0;
  $("reason-field").hidden = unban;
  $("duration-field").hidden = unban;
  $("scope-field").hidden = !scopeVisible();
  $("unban-hint").hidden = !unban;
  $("ban-submit").className = unban ? "primary wide" : "danger wide";
  $("ban-submit").textContent = unban
    ? (count > 1 ? t("unbanInN", count) : t("unbanOne"))
    : (count > 1 ? t("banInN", count) : t("banOne"));
}

for (const radio of $("tab-ban").elements.mode) {
  radio.onchange = () => {
    renderTargets();   // ban ve kaldırmada kanal seçimi geçerli olabilir; hedef satırı ve düğme yenilenir
    saveDraft();
    $("ban-result").replaceChildren();
  };
}

// Kanal seçimi: ban hangi kanallarda atılsın. Varsayılan "Tümü"; "Sadece benimki" kendi kanalında, "Seç" işaretlenen
// kanallarda banlar ya da banı kaldırır. Yalnızca ekipte birden çok kanal varsa görünür. Seçim işlem yapılana dek
// taslakla saklanır, işlem yapılınca "Tümü"ne döner.
// Ban kaldırmada seçimi 0.15.0 öncesi sunucu tanımaz ve bütün kanallarda kaldırırdı; orada seçici gizlenir.
const scopeEnabled = () => Boolean(state.scopeSupported && (!unbanMode() || state.unbanScopeSupported));
const scopeVisible = () => Boolean(scopeEnabled() && state.team && state.team.channels.length > 1);

// Banın uygulanacağı kanallar. channels: sunucuya gidecek kimlikler; seçim yoksa ya da hepsi seçiliyse null.
function resolveScope() {
  const all = state.team ? state.team.channels : [];
  let list = all;
  if (scopeEnabled() && all.length > 1) {
    const { mode, ids } = state.scope;
    if (mode === "own") {
      const own = all.filter((c) => c.broadcaster_id === state.me.user.id);
      if (own.length) list = own;
    } else if (mode === "custom") {
      list = all.filter((c) => ids.includes(c.broadcaster_id));
    }
  }
  const partial = list.length > 0 && list.length < all.length;
  return { list, channels: partial ? list.map((c) => c.broadcaster_id) : null };
}

function renderTargets() {
  const slugs = resolveScope().list.map((c) => c.slug);
  $("targets").textContent = slugs.length ? t("targets", slugs.length, slugs.join(", ")) : t("scopeNone");
  syncMode();
}

function renderScope() {
  const channels = state.team ? state.team.channels : [];
  const scope = state.scope;
  const own = channels.some((c) => c.broadcaster_id === state.me.user.id);
  // Ekipten çıkarılan kanal seçimden düşer; kendi kanalı listede yoksa "sadece benimki" geçersizdir.
  scope.ids = scope.ids.filter((id) => channels.some((c) => c.broadcaster_id === id));
  if (scope.mode === "own" && !own) scope.mode = "all";
  $("scope-field").hidden = !scopeVisible();
  $("scope-own").hidden = !own;
  for (const radio of $("tab-ban").elements.scope) radio.checked = radio.value === scope.mode;
  $("scope-list").hidden = scope.mode !== "custom";
  $("scope-list").replaceChildren(...channels.map((c) => {
    const box = el("input", { type: "checkbox", checked: scope.ids.includes(c.broadcaster_id) });
    box.onchange = () => {
      scope.ids = box.checked ? [...scope.ids, c.broadcaster_id] : scope.ids.filter((id) => id !== c.broadcaster_id);
      renderTargets();
      saveDraft();
    };
    return el("li", {}, el("label", { className: "switch" }, box, el("span", { className: "mono", textContent: c.slug })));
  }));
  renderTargets();
}

for (const radio of $("tab-ban").elements.scope) {
  radio.onchange = () => {
    state.scope.mode = radio.value;
    // "Seç" ilk açıldığında hepsi işaretlidir: çoğu zaman bir iki kanalı çıkarmak istenir.
    if (radio.value === "custom" && !state.scope.ids.length && state.team) {
      state.scope.ids = state.team.channels.map((c) => c.broadcaster_id);
    }
    renderScope();
    saveDraft();
  };
}

function resetScope() {
  state.scope = { mode: "all", ids: [] };
  if (state.team) renderScope();
  saveDraft();
}

// Kanal seçimini tanımayan eski sunucu `channels` alanını yok sayıp banı bütün kanallara uygulardı;
// bu yüzden seçici yalnızca 0.14.0 ve sonrasında görünür.
async function checkScopeSupport() {
  const ok = await serverAtLeast(0, 14, 0);
  const unbanOk = await serverAtLeast(0, 15, 0);
  if (ok === state.scopeSupported && unbanOk === state.unbanScopeSupported) return;
  state.scopeSupported = ok;
  state.unbanScopeSupported = unbanOk;
  if (state.team) renderScope();
}

// Sunucunun sürümü en az istenen kadar mı (/health). Yanıt yoksa eski sunucu sayılır. Başarılı yanıt saklanır.
let versionCache = { server: null, have: [] };
async function serverAtLeast(...want) {
  const server = state.server;
  if (versionCache.server !== server) {
    const res = await api("GET", "/health").catch(() => null);
    if (!res) return false;
    versionCache = { server, have: String(res.version || "0").split(".").map(Number) };
  }
  const { have } = versionCache;
  for (const [i, part] of want.entries()) {
    if ((have[i] || 0) !== part) return (have[i] || 0) > part;
  }
  return true;
}

// Kaldırma sıraya gitmez; panel kapanırsa yarıda kalmasın diye tek seferde az kişi alınır.

// Uzun kaldırma listesi, toplu ban gibi sunucudaki sıraya gider; panel kapansa da işlenir.
// Kısa listeler eskisi gibi tek tek kaldırılır ve sonuçları hemen görünür.
function submitUnban(form, button, usernames) {
  const target = resolveScope();
  if (!target.list.length) {
    showMessage(t("scopeNone"));
    return;
  }
  if (usernames.length > MAX_IMPORT) {
    showMessage(t("banLimit", MAX_IMPORT, usernames.length));
    return;
  }
  const label = button.textContent;
  run(button, async () => {
    const who = usernames.length === 1 ? usernames[0] : t("userCount", usernames.length);
    // Seçim yapıldıysa onay metni kanalları söyler; sunucuya yalnızca gerçek seçim gider.
    const count = target.list.length;
    const extra = target.channels ? { channels: target.channels } : {};
    const where = target.channels ? `${t("scopeOnly", target.list.map((c) => c.slug).join(", "))} ` : "";
    if (usernames.length > QUEUE_THRESHOLD) {
      // 0.12.1 öncesi sunucu sıradaki işlemin türünü tanımaz ve listeyi banlar; orada eski sınır geçerli.
      if (!(await serverAtLeast(0, 12, 1))) throw new Error(t("unbanLimit", QUEUE_THRESHOLD, usernames.length));
      if (!(await ask(where + t("confirmUnbanQueue", who, count)))) return;
      const { added, skipped } = await api("POST", `/teams/${state.teamId}/imports`, { usernames, action: "unban", ...extra });
      form.username.value = "";
      resetScope();
      updateNameCount();
      $("ban-result").replaceChildren();
      showMessage(t("queued", added, skipped), "info");
      await pollQueue();
      return;
    }
    if (!(await ask(where + t("confirmUnban", who, count)))) return;
    const failed = [];
    $("ban-result").replaceChildren();
    try {
      for (const [index, username] of usernames.entries()) {
        button.textContent = t("unbanning", index + 1, usernames.length);
        try {
          const ban = await api("POST", `/teams/${state.teamId}/unbans`, { username, ...extra });
          $("ban-result").prepend(banCard(ban));
        } catch (e) {
          if (!state.token) throw e;
          // 0.6.0 öncesi sunucu bu yolu tanımaz; yalın "Bulunamadı" kullanıcıya bir şey söylemez.
          if (e.message === "Bulunamadı") {
            throw new Error(t("oldServerUnban"));
          }
          failed.push(username);
          $("ban-result").prepend(el("div", { className: "ban error" },
            el("div", { className: "head" }, el("span", { className: "name", textContent: username })),
            el("div", { className: "reason", textContent: e.message })));
        }
      }
    } finally {
      button.textContent = label;
    }
    form.username.value = failed.join("\n");
    updateNameCount();
    if (failed.length) showMessage(t("unbanFailedN", failed.length));
    else resetScope();
    await loadBans();
  });
}

$("tab-ban").onsubmit = (event) => {
  event.preventDefault();
  const form = event.target;
  const button = $("ban-submit");
  const label = button.textContent;
  const usernames = parseUsernames(form.username.value);
  const count = state.team ? state.team.channels.length : 0;
  if (!count) {
    showMessage(t("needChannel"));
    return;
  }
  if (!usernames.length) return;
  if (unbanMode()) return submitUnban(form, button, usernames);
  const target = resolveScope();
  if (!target.list.length) {
    showMessage(t("scopeNone"));
    return;
  }
  if (usernames.length > MAX_IMPORT) {
    showMessage(t("banLimit", MAX_IMPORT, usernames.length));
    return;
  }
  run(button, async () => {
    const who = usernames.length === 1 ? usernames[0] : t("userCount", usernames.length);
    const reason = form.reason.value.trim();
    const duration = form.duration.value ? Number(form.duration.value) : null;
    const how = duration ? t("howTimed", formatDuration(duration)) : t("howPerm");
    // Seçim yapıldıysa onay metni hangi kanallar olduğunu da söyler; sunucuya yalnızca gerçek seçim gider.
    const extra = target.channels ? { channels: target.channels } : {};
    const where = target.channels ? `${t("scopeOnly", target.list.map((c) => c.slug).join(", "))} ` : "";
    if (usernames.length > QUEUE_THRESHOLD) {
      if (!(await ask(where + t("confirmQueue", who, target.list.length, how)))) return;
      const { added, skipped } = await api("POST", `/teams/${state.teamId}/imports`, { usernames, reason, duration, ...extra });
      form.username.value = "";
      form.reason.value = "";
      resetScope();
      syncPresets();
      updateNameCount();
      $("ban-result").replaceChildren();
      showMessage(t("queued", added, skipped), "info");
      await pollQueue();
      return;
    }
    if (!(await ask(where + t("confirmBan", who, target.list.length, how)))) return;
    const failed = [];
    $("ban-result").replaceChildren();
    try {
      for (const [index, username] of usernames.entries()) {
        button.textContent = t("banning", index + 1, usernames.length);
        try {
          const ban = await api("POST", `/teams/${state.teamId}/bans`, { username, reason, duration, ...extra });
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
      resetScope();
      syncPresets();
    } else {
      showMessage(t("banFailedN", failed.length));
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
  } else if (changes.pendingInvite?.newValue && !$("app-view").classList.contains("loading")) {
    // Panel açıkken davet sayfasında Ekibe katıl'a basıldı.
    handlePendingInvite();
  }
});

// Sekme adları bazı dillerde uzun; sayaç da büyüyebilir. Sığmazlarsa simgeler gizlenir, adlar kalır.
function fitTabs() {
  const tabs = document.querySelector(".tabs");
  tabs.classList.remove("compact");
  tabs.classList.toggle("compact", tabs.scrollWidth > tabs.clientWidth + 1);
}
// Sekmeler ekip seçilince görünür hale gelir; o an ölçülür.
new ResizeObserver(fitTabs).observe(document.querySelector(".tabs"));

// Ayarlar başlıktaki dişliyle açılır. Açıkken giriş ve uygulama görünümleri CSS ile gizlenir; kapanınca
// oldukları gibi geri gelir, panel yeniden yüklenmez.
function toggleSettings(open = !document.body.classList.contains("settings-open")) {
  document.body.classList.toggle("settings-open", open);
  $("settings-view").hidden = !open;
  $("settings-toggle").setAttribute("aria-expanded", String(open));
  scrollTo(0, 0);
}

$("settings-toggle").onclick = () => toggleSettings();
$("settings-close").onclick = () => toggleSettings(false);
addEventListener("keydown", (event) => {
  if (event.key === "Escape" && document.body.classList.contains("settings-open") && !$("confirm").open) {
    toggleSettings(false);
  }
});

// Diller kendi adlarıyla listelenir; seçim saklanır ve panel yeni dille baştan açılır.
function renderSettings() {
  $("lang-select").replaceChildren(...LANGS.map((lang) =>
    el("option", { value: lang, lang, textContent: LANG_NAMES[lang], selected: lang === LANG })));
  const version = chrome.runtime.getManifest().version;
  $("version").textContent = version ? t("version", version) : "";
}

$("lang-select").onchange = async () => {
  await chrome.storage.local.set({ lang: $("lang-select").value });
  location.reload();
};

(async () => {
  await loadLang();
  applyI18n();
  renderSettings();
  const stored = await chrome.storage.local.get(["server", "token", "teamId"]);
  state.server = stored.server || DEFAULT_SERVER;
  state.token = stored.token || null;
  state.teamId = stored.teamId || null;
  // Eski sürümlerin kaydettiği şifresiz adresle oturum açılmaz; kullanıcı adresi düzeltip yeniden giriş yapar.
  const serverProblem = serverUrlProblem(state.server);
  if (serverProblem) state.token = null;
  // Yarım kalan form geri gelir; sağ tık menüsünden açıldıysa seçilen ad da eklenir.
  await restoreDraft(new URLSearchParams(location.search).get("user") || "");
  await render();
  if (serverProblem) {
    $("server").closest("details").open = true;
    showMessage(t("storedServerBad", serverProblem));
  }
})();
