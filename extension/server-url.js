// Panel ve service worker ortak kullanır: token yalnızca şifreli (https://) bağlantıyla gider.
// Şifresiz http:// yalnızca bu bilgisayardaki sunucu için (yerel deneme) kabul edilir.
const LOOPBACK_HOSTS = ["localhost", "127.0.0.1", "[::1]"];

// Adres kullanılabilirse null, değilse kullanıcıya gösterilecek açıklamayı döndürür.
function serverUrlProblem(server) {
  let url;
  try {
    url = new URL(server);
  } catch {
    return "Sunucu adresi geçersiz. https:// ile başlayan tam adresi yaz.";
  }
  if (url.protocol === "https:") return null;
  if (url.protocol === "http:" && LOOPBACK_HOSTS.includes(url.hostname)) return null;
  if (url.protocol === "http:") {
    return "Bu sunucu şifresiz (http://) bağlantı kullanıyor; oturum bilgin başkalarınca okunabilir. https:// ile başlayan adresi yaz.";
  }
  return "Sunucu adresi https:// ile başlamalı.";
}
