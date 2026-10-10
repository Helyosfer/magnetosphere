// Giriş akışı burada çalışır: Kick penceresi açılınca popup kapanır, service worker açık kalır.
async function login(server) {
  const redirect = chrome.identity.getRedirectURL();
  const url = `${server}/auth/login?redirect=${encodeURIComponent(redirect)}`;
  const finalUrl = await chrome.identity.launchWebAuthFlow({ url, interactive: true });
  const token = new URLSearchParams(new URL(finalUrl).hash.slice(1)).get("token");
  if (!token) throw new Error("Sunucu oturum döndürmedi");
  await chrome.storage.local.set({ token });
}

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg.type !== "login") return;
  login(msg.server).then(
    () => sendResponse({ ok: true }),
    (e) => sendResponse({ ok: false, error: String(e.message || e) })
  );
  return true;
});

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "crossban",
    title: "Ekibin tüm kanallarında banla",
    contexts: ["selection", "link"],
    documentUrlPatterns: ["https://kick.com/*", "https://*.kick.com/*"],
  });
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
