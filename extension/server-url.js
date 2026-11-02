// Panel ve service worker ortak kullanır (önce i18n.js yüklenir): token yalnızca şifreli (https://) bağlantıyla gider.
// Şifresiz http:// yalnızca bu bilgisayardaki sunucu için (yerel deneme) kabul edilir.
const DEFAULT_SERVER = "https://magnetosphere.helyosfer.me";
const LOOPBACK_HOSTS = ["localhost", "127.0.0.1", "[::1]"];

// Adres kullanılabilirse null, değilse kullanıcıya gösterilecek açıklamayı döndürür.
function serverUrlProblem(server) {
  let url;
  try {
    url = new URL(server);
  } catch {
    return t("serverInvalid");
  }
  if (url.protocol === "https:") return null;
  if (url.protocol === "http:" && LOOPBACK_HOSTS.includes(url.hostname)) return null;
  if (url.protocol === "http:") {
    return t("serverHttp");
  }
  return t("serverHttps");
}
