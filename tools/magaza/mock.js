// Mağaza görselleri için paneli sunucusuz çalıştırır: chrome.* ve sunucu yanıtları örnek veriyle taklit edilir.
// tools/magaza_gorselleri.py bu dosyayı panel.html'in en başına ekler. Adres: panel.html?scene=<ad>&lang=<dil>
(() => {
  const params = new URLSearchParams(location.search);
  const SCENE = params.get("scene") || "ban";

  // Örnek adlar ve sebepler görselin dilinde. Kick kullanıcı adları Latin harfli olduğu için Arapçada da öyle kalır.
  const NAMES = {
    tr: { team: "Örnek", ch2: "kanal2", mate: "modarkadas", admin: "yardimci_yonetici", viewer: "izleyen_biri",
          troll: "trolcu_mehmet", toxic: "kufurbaz99", long: "cok_uzun_bir_kullanici_adi_ornegi",
          spam: "Spam botu", trollR: "Trol",
          longR: "Taciz; birden fazla kanalda aynı mesajları tekrar tekrar gönderdi" },
    en: { team: "Example", ch2: "channel2", mate: "modbuddy", admin: "co_admin", viewer: "lurker42",
          troll: "troll_master", toxic: "toxic_guy99", long: "a_really_long_username_example",
          spam: "Spam bot", trollR: "Troll",
          longR: "Harassment; sent the same messages over and over in several channels" },
    es: { team: "Ejemplo", ch2: "canal2", mate: "mod_amigo", admin: "co_admin", viewer: "mirando42",
          troll: "el_troll_mayor", toxic: "toxico99", long: "un_usuario_muy_largo_de_ejemplo",
          spam: "Bot de spam", trollR: "Troll",
          longR: "Acoso; mandó los mismos mensajes una y otra vez en varios canales" },
    pt: { team: "Exemplo", ch2: "canal2", mate: "parceiro_mod", admin: "co_admin", viewer: "so_olhando",
          troll: "trollzinho", toxic: "toxico99", long: "um_nome_de_usuario_bem_longo",
          spam: "Bot de spam", trollR: "Troll",
          longR: "Assédio; mandou as mesmas mensagens várias vezes em vários canais" },
    ar: { team: "مثال", ch2: "channel2", mate: "mod_ahmed", admin: "co_admin", viewer: "lurker42",
          troll: "troll_king", toxic: "toxic99", long: "a_really_long_username_example",
          spam: "بوت سبام", trollR: "تخريب",
          longR: "تحرّش؛ أرسل الرسائل نفسها مرارًا في عدة قنوات" },
  };
  const L = params.get("lang") in NAMES ? params.get("lang") : "en";
  const N = NAMES[L];

  const now = Math.floor(Date.now() / 1000);
  const me = { id: 1, name: "Helyosfer" };
  const ok = (slug) => ({ slug, status: "ok" });
  const sept4 = Math.floor(new Date(new Date().getFullYear(), 8, 4, 21, 14).getTime() / 1000);

  const bans = [
    { id: 4, target_name: "spam_bot_4821", reason: N.spam, duration: null, created_by: "Helyosfer", created_by_id: 1,
      created_at: now - 180, results: [ok("helyosfer"), ok(N.ch2)] },
    { id: 3, target_name: N.troll, reason: N.trollR, duration: 1440, created_by: N.mate, created_by_id: 2,
      created_at: now - 5 * 3600, results: [ok("helyosfer"), { slug: N.ch2, status: "failed" }] },
    { id: 2, target_name: N.toxic, reason: "", duration: 10080, created_by: "Helyosfer", created_by_id: 1,
      created_at: now - 2 * 86400, results: [ok("helyosfer"), ok(N.ch2)] },
    { id: 1, target_name: N.long, reason: N.longR, duration: null, created_by: N.mate, created_by_id: 2,
      created_at: sept4, results: [ok("helyosfer"), ok(N.ch2)] },
  ];

  const team = {
    id: 1, name: N.team, role: "owner", lend: true, invite_code: "MGN-7Q4K-2XPA", join_role: "mod",
    channels: [
      { slug: "helyosfer", broadcaster_id: 1, broadcaster_joined: true },
      { slug: N.ch2, broadcaster_id: 7 },
    ],
    members: [
      { id: 1, name: "Helyosfer", role: "owner" },
      { id: 2, name: N.mate, role: "mod" },
      { id: 3, name: N.admin, role: "admin" },
      { id: 4, name: N.viewer, role: "viewer" },
    ],
  };

  const queue = SCENE === "queue"
    ? { total: 120, counts: { pending: 72, done: 43, notfound: 5 },
        problems: [191, 207, 233, 250, 268].map((n) => ({ name: `bot_0${n}`, status: "notfound" })) }
    : { total: 0, counts: {}, problems: [] };

  function answer(method, path) {
    const url = new URL(path, "https://x");
    if (url.pathname === "/me") return { user: me, teams: [{ id: 1, name: N.team }], can_create_team: true };
    if (url.pathname === "/teams/1") return team;
    if (url.pathname === "/teams/1/imports") return queue;
    if (url.pathname === "/teams/1/bans") return { bans, matched: bans.length, active_total: bans.length };
    return {};
  }

  window.fetch = async (url, options = {}) => {
    const path = String(url).replace(/^https?:\/\/[^/]+/, "");
    const body = JSON.stringify(answer(options.method || "GET", path));
    return new Response(body, { status: 200, headers: { "Content-Type": "application/json" } });
  };

  const store = { token: "demo", teamId: 1, lang: L, server: "https://magnetosphere.helyosfer.me" };
  window.chrome = {
    i18n: { getUILanguage: () => L },
    runtime: { sendMessage: async () => ({ ok: true }) },
    storage: {
      local: {
        get: async (keys) => {
          const list = Array.isArray(keys) ? keys : [keys];
          return Object.fromEntries(list.filter((k) => k in store).map((k) => [k, store[k]]));
        },
        set: async (items) => Object.assign(store, items),
        remove: async () => {},
      },
      onChanged: { addListener() {} },
    },
  };

  // Geçiş animasyonları kapalı: çekim anında sekmeler yarı saydam kalmasın.
  document.addEventListener("DOMContentLoaded", () => {
    document.head.append(Object.assign(document.createElement("style"), {
      textContent: "*, *::before, *::after { animation: none !important; transition: none !important; }",
    }));
  });

  // Panel açılınca sahneyi kur; bitince çekim betiği için işaret bırak.
  const SETUP = {
    ban() {
      document.getElementById("username").value = "spam_bot_4821\nspam_bot_4822";
    },
    queue() {
      document.getElementById("username").value = "bot_0191\nbot_0192\nbot_0193\nbot_0194";
    },
    list() { document.querySelector('.tabs [data-tab="list"]').click(); },
    crew() { document.querySelector('.tabs [data-tab="crew"]').click(); },
  };

  const wait = setInterval(() => {
    const view = document.getElementById("team-view");
    if (!view || view.hidden || !document.getElementById("list-count").textContent) return;
    clearInterval(wait);
    (SETUP[SCENE] || SETUP.ban)();
    const username = document.getElementById("username");
    username.dispatchEvent(new Event("input"));
    if (SCENE === "ban" || SCENE === "queue") {
      const reason = document.getElementById("reason");
      reason.value = N.spam;
      reason.dispatchEvent(new Event("input"));
    }
    setTimeout(() => { document.documentElement.dataset.ready = "1"; }, 300);
  }, 30);
})();
