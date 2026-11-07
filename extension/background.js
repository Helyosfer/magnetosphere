importScripts("i18n.js", "server-url.js");

// Giriş akışı burada çalışır: Kick penceresi açılınca popup kapanır, service worker açık kalır.
async function login(server) {
  await loadLang();
  // Panel de denetler; burada tekrar bakılır ki başka yoldan gelen mesaj token'ı şifresiz adrese taşımasın.
  const problem = serverUrlProblem(server);
  if (problem) throw Object.assign(new Error(problem), { friendly: true });
  const redirect = chrome.identity.getRedirectURL();
  const url = `${server}/auth/login?redirect=${encodeURIComponent(redirect)}&lang=${LANG}`;
  const finalUrl = await chrome.identity.launchWebAuthFlow({ url, interactive: true });
  const params = new URLSearchParams(new URL(finalUrl).hash.slice(1));
  // Sunucu, Kick tarafındaki hatayı kullanıcıya gösterilecek hazır bir mesajla döndürür.
  if (params.get("error")) throw Object.assign(new Error(params.get("error")), { friendly: true });
  const token = params.get("token");
  if (!token) throw new Error(t("noSession"));
  await chrome.storage.local.set({ token });
}

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg.type !== "login") return;
  login(msg.server).then(
    () => sendResponse({ ok: true }),
    (e) => sendResponse({ ok: false, error: String(e.message || e), friendly: Boolean(e.friendly) })
  );
  return true;
});

// Davet sayfası (sunucunun /join adresi) kodu buraya verir. Katılma kendiliğinden olmaz: panel açılınca
// kullanıcıya sorulur. Hangi sitelerin mesaj atabileceğini manifest'teki externally_connectable belirler.
const INVITE_ORIGINS = ["https://magnetosphere.helyosfer.me"];

chrome.runtime.onMessageExternal.addListener((msg, sender, sendResponse) => {
  if (!INVITE_ORIGINS.includes(sender.origin)) return;
  if (msg?.type === "ping") return sendResponse({ ok: true });
  if (msg?.type !== "invite" || !/^[A-Za-z0-9_-]{6,64}$/.test(msg.code || "")) return sendResponse({ ok: false });
  (async () => {
    await chrome.storage.local.set({ pendingInvite: { code: msg.code, server: sender.origin, at: Date.now() } });
    // Panel kendiliğinden açılamazsa (eski Chrome, odakta olmayan pencere) sayfa simgeye tıklamayı söyler.
    let opened = false;
    try {
      await chrome.action.openPopup();
      opened = true;
    } catch {}
    return { ok: true, opened };
  })().then(sendResponse, () => sendResponse({ ok: false }));
  return true;
});

chrome.runtime.onInstalled.addListener(async () => {
  await loadLang();
  chrome.contextMenus.create({
    id: "crossban",
    title: t("contextMenu"),
    contexts: ["selection", "link"],
    documentUrlPatterns: ["https://kick.com/*", "https://*.kick.com/*"],
  });
});

// Panelden dil değişince sağ tık menüsü de o dile geçer.
chrome.storage.onChanged.addListener(async (changes) => {
  if (!("lang" in changes)) return;
  await loadLang();
  chrome.contextMenus.update("crossban", { title: t("contextMenu") });
});

chrome.contextMenus.onClicked.addListener((info) => {
  if (info.menuItemId !== "crossban") return;
  let user = (info.selectionText || "").trim();
  if (!user && info.linkUrl) {
    user = new URL(info.linkUrl).pathname.split("/").filter(Boolean)[0] || "";
  }
  chrome.windows.create({
    url: chrome.runtime.getURL(`panel.html?user=${encodeURIComponent(user)}`),
    type: "popup",
    width: 440,
    height: 680,
  });
});
