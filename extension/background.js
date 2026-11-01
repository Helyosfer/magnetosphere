importScripts("server-url.js");

// Giriş akışı burada çalışır: Kick penceresi açılınca popup kapanır, service worker açık kalır.
async function login(server) {
  // Panel de denetler; burada tekrar bakılır ki başka yoldan gelen mesaj token'ı şifresiz adrese taşımasın.
  const problem = serverUrlProblem(server);
  if (problem) throw Object.assign(new Error(problem), { friendly: true });
  const redirect = chrome.identity.getRedirectURL();
  const url = `${server}/auth/login?redirect=${encodeURIComponent(redirect)}`;
  const finalUrl = await chrome.identity.launchWebAuthFlow({ url, interactive: true });
  const params = new URLSearchParams(new URL(finalUrl).hash.slice(1));
  // Sunucu, Kick tarafındaki hatayı kullanıcıya gösterilecek hazır bir mesajla döndürür.
  if (params.get("error")) throw Object.assign(new Error(params.get("error")), { friendly: true });
  const token = params.get("token");
  if (!token) throw new Error("Sunucu oturum döndürmedi");
  await chrome.storage.local.set({ token });
}

// kick.com'daki kullanıcı kartı sorar: kullanıcı seçili ekibin kaç kanalında banlı.
// Token yalnızca burada kullanılır; içerik betiğine sadece sonuç döner.
async function userBans(username) {
  if (typeof username !== "string" || !/^[A-Za-z0-9_-]{1,25}$/.test(username)) return { ok: false };
  const { token, teamId, server: stored } = await chrome.storage.local.get(["token", "teamId", "server"]);
  const server = stored || DEFAULT_SERVER;
  if (!token || !teamId || serverUrlProblem(server)) return { ok: false };
  const res = await fetch(`${server}/teams/${Number(teamId)}/users/${username}/bans`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) return { ok: false };
  return { ok: true, bans: await res.json() };
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === "userBans") {
    // Yalnızca bu uzantının kick.com'daki içerik betiği sorabilir.
    if (sender.id !== chrome.runtime.id || !/^https:\/\/(www\.)?kick\.com\//.test(sender.url || "")) return;
    userBans(msg.username).then(sendResponse, () => sendResponse({ ok: false }));
    return true;
  }
  if (msg.type !== "login") return;
  login(msg.server).then(
    () => sendResponse({ ok: true }),
    (e) => sendResponse({ ok: false, error: String(e.message || e), friendly: Boolean(e.friendly) })
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
