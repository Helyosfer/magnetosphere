// Davet sayfası. Kod adresin # kısmında durur; tarayıcı bu kısmı sunucuya göndermez, günlüğe de düşmez.
// Eklenti kuruluysa kod ona doğrudan verilir (manifest'teki externally_connectable), değilse kopyalanıp
// panele yapıştırılır.
(() => {
  const TEXT = {
    tr: {
      title: "Magnetosphere ekibine davet edildin",
      lead: "Ekibe katılınca bir kanalda atılan ban ekibin bütün kanallarında uygulanır.",
      stepInstall: "Magnetosphere eklentisini Chrome'a kur.",
      stepJoin: "Bu sayfaya dön ve Ekibe katıl'a bas; ya da kodu kopyalayıp eklentideki davet kodu alanına yapıştır.",
      stepJoinReady: "Ekibe katıl'a bas, eklentide çıkan onayı kabul et.",
      copy: "Kopyala", copied: "Kopyalandı",
      install: "Chrome Web Store'dan kur", join: "Ekibe katıl",
      mobile: "Magnetosphere bilgisayardaki Chrome'da çalışır; telefonda kurulamaz. Bu bağlantıyı bilgisayarında aç.",
      otherBrowser: "Magnetosphere bu tarayıcıda çalışmaz. Bu bağlantıyı bilgisayarında Chrome'da (ya da Edge, Brave gibi Chromium tabanlı bir tarayıcıda) aç.",
      copyLink: "Bağlantıyı kopyala", linkCopied: "Bağlantı kopyalandı",
      reloadHint: "Kurulum bittiyse sayfayı yenile.", reload: "Yenile",
      sent: "Davet eklentiye iletildi. Açılmadıysa Chrome'un sağ üstündeki Magnetosphere simgesine tıkla; katılma onayı seni bekliyor.",
      sentOpened: "Eklenti açıldı; katılmayı oradan onayla.",
      failed: "Davet eklentiye iletilemedi. Kodu kopyalayıp eklentiye yapıştırabilirsin.",
      missing: "Bu bağlantıda davet kodu yok. Seni davet eden kişiden bağlantıyı yeniden iste.",
    },
    en: {
      title: "You're invited to a Magnetosphere team",
      lead: "Once you join, a ban on one channel is applied on all of the team's channels.",
      stepInstall: "Install the Magnetosphere extension in Chrome.",
      stepJoin: "Come back to this page and press Join team, or copy the code and paste it into the invite code field in the extension.",
      stepJoinReady: "Press Join team and accept the prompt in the extension.",
      copy: "Copy", copied: "Copied",
      install: "Install from the Chrome Web Store", join: "Join team",
      mobile: "Magnetosphere runs in Chrome on a computer; it can't be installed on a phone. Open this link on your computer.",
      otherBrowser: "Magnetosphere doesn't work in this browser. Open this link in Chrome on your computer (or a Chromium-based browser like Edge or Brave).",
      copyLink: "Copy link", linkCopied: "Link copied",
      reloadHint: "Finished installing? Reload this page.", reload: "Reload",
      sent: "The invite was passed to the extension. If it didn't open, click the Magnetosphere icon at the top right of Chrome; the join prompt is waiting.",
      sentOpened: "The extension opened; confirm joining there.",
      failed: "Couldn't pass the invite to the extension. You can copy the code and paste it into the extension.",
      missing: "This link has no invite code. Ask the person who invited you to send it again.",
    },
    es: {
      title: "Te invitaron a un equipo de Magnetosphere",
      lead: "Al unirte, un baneo en un canal se aplica en todos los canales del equipo.",
      stepInstall: "Instala la extensión Magnetosphere en Chrome.",
      stepJoin: "Vuelve a esta página y pulsa Unirse al equipo, o copia el código y pégalo en el campo de código de invitación de la extensión.",
      stepJoinReady: "Pulsa Unirse al equipo y acepta la confirmación en la extensión.",
      copy: "Copiar", copied: "Copiado",
      install: "Instalar desde Chrome Web Store", join: "Unirse al equipo",
      mobile: "Magnetosphere funciona en Chrome en una computadora; no se puede instalar en el teléfono. Abre este enlace en tu computadora.",
      otherBrowser: "Magnetosphere no funciona en este navegador. Abre este enlace en Chrome en tu computadora (o en un navegador basado en Chromium, como Edge o Brave).",
      copyLink: "Copiar enlace", linkCopied: "Enlace copiado",
      reloadHint: "¿Terminó la instalación? Recarga esta página.", reload: "Recargar",
      sent: "La invitación se pasó a la extensión. Si no se abrió, haz clic en el icono de Magnetosphere arriba a la derecha en Chrome; la confirmación te espera.",
      sentOpened: "La extensión se abrió; confirma allí que quieres unirte.",
      failed: "No se pudo pasar la invitación a la extensión. Puedes copiar el código y pegarlo en la extensión.",
      missing: "Este enlace no tiene código de invitación. Pide a quien te invitó que lo envíe de nuevo.",
    },
    pt: {
      title: "Você foi convidado para uma equipe do Magnetosphere",
      lead: "Depois de entrar, um ban em um canal é aplicado em todos os canais da equipe.",
      stepInstall: "Instale a extensão Magnetosphere no Chrome.",
      stepJoin: "Volte a esta página e clique em Entrar na equipe, ou copie o código e cole no campo de código de convite da extensão.",
      stepJoinReady: "Clique em Entrar na equipe e aceite a confirmação na extensão.",
      copy: "Copiar", copied: "Copiado",
      install: "Instalar pela Chrome Web Store", join: "Entrar na equipe",
      mobile: "O Magnetosphere funciona no Chrome do computador; não dá para instalar no celular. Abra este link no seu computador.",
      otherBrowser: "O Magnetosphere não funciona neste navegador. Abra este link no Chrome do seu computador (ou em um navegador baseado em Chromium, como Edge ou Brave).",
      copyLink: "Copiar link", linkCopied: "Link copiado",
      reloadHint: "Terminou de instalar? Recarregue esta página.", reload: "Recarregar",
      sent: "O convite foi passado para a extensão. Se ela não abriu, clique no ícone do Magnetosphere no canto superior direito do Chrome; a confirmação está esperando.",
      sentOpened: "A extensão abriu; confirme a entrada por lá.",
      failed: "Não foi possível passar o convite para a extensão. Você pode copiar o código e colar na extensão.",
      missing: "Este link não tem código de convite. Peça para quem te convidou enviar de novo.",
    },
    ar: {
      title: "تمت دعوتك إلى فريق في Magnetosphere",
      lead: "بعد الانضمام، يُطبَّق الحظر في قناة واحدة على جميع قنوات الفريق.",
      stepInstall: "ثبّت إضافة Magnetosphere في Chrome.",
      stepJoin: "عُد إلى هذه الصفحة واضغط «الانضمام إلى الفريق»، أو انسخ الرمز والصقه في حقل رمز الدعوة في الإضافة.",
      stepJoinReady: "اضغط «الانضمام إلى الفريق» ثم وافق على التأكيد في الإضافة.",
      copy: "نسخ", copied: "تم النسخ",
      install: "التثبيت من Chrome Web Store", join: "الانضمام إلى الفريق",
      mobile: "يعمل Magnetosphere في Chrome على الكمبيوتر ولا يمكن تثبيته على الهاتف. افتح هذا الرابط على جهاز الكمبيوتر.",
      otherBrowser: "لا يعمل Magnetosphere في هذا المتصفح. افتح هذا الرابط في Chrome على جهاز الكمبيوتر (أو في متصفح مبني على Chromium مثل Edge أو Brave).",
      copyLink: "نسخ الرابط", linkCopied: "تم نسخ الرابط",
      reloadHint: "هل انتهى التثبيت؟ أعد تحميل هذه الصفحة.", reload: "إعادة التحميل",
      sent: "تم تمرير الدعوة إلى الإضافة. إن لم تُفتح، انقر أيقونة Magnetosphere أعلى يمين Chrome؛ تأكيد الانضمام بانتظارك.",
      sentOpened: "فُتحت الإضافة؛ أكّد الانضمام من هناك.",
      failed: "تعذّر تمرير الدعوة إلى الإضافة. يمكنك نسخ الرمز ولصقه في الإضافة.",
      missing: "لا يحتوي هذا الرابط على رمز دعوة. اطلب من الشخص الذي دعاك إرساله مرة أخرى.",
    },
  };
  const STORE_ID = "kjbbjooackbcfeeoolkfpmdbkomjiflh";
  const lang = (navigator.languages || [navigator.language || "en"])
    .map((l) => l.slice(0, 2).toLowerCase()).find((l) => TEXT[l]) || "en";
  const t = TEXT[lang];
  const $ = (id) => document.getElementById(id);
  document.documentElement.lang = lang;
  document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
  document.title = t.title;
  $("title").textContent = t.title;

  // Aynı sekmede yalnızca # kısmı değişirse tarayıcı sayfayı yenilemez; yeni kod için baştan yüklenir.
  addEventListener("hashchange", () => location.reload());
  let code = "";
  try {
    code = decodeURIComponent(location.hash.slice(1)).trim();
  } catch {}
  if (!/^[A-Za-z0-9_-]{6,64}$/.test(code)) {
    $("lead").textContent = t.missing;
    $("lead").classList.add("error");
    return;
  }
  $("lead").textContent = t.lead;
  $("step-install").textContent = t.stepInstall;
  $("step-join").textContent = t.stepJoin;
  $("code").textContent = code;
  $("copy").textContent = t.copy;
  $("install").textContent = t.install;
  $("join").textContent = t.join;
  $("copy-link").textContent = t.copyLink;
  $("reload-hint").textContent = t.reloadHint;
  $("reload").textContent = t.reload;
  $("invite").hidden = false;

  async function copyText(text, button, done, idle) {
    try {
      await navigator.clipboard.writeText(text);
      button.textContent = done;
      setTimeout(() => { button.textContent = idle; }, 1500);
    } catch {
      getSelection().selectAllChildren($("code"));
    }
  }
  $("copy").onclick = () => copyText(code, $("copy"), t.copied, t.copy);
  $("copy-link").onclick = () => copyText(location.href, $("copy-link"), t.linkCopied, t.copyLink);
  $("reload").onclick = () => location.reload();

  // Modlar bağlantıyı çoğunlukla Discord ya da WhatsApp'tan, yani telefondan açar. Eklenti yalnızca
  // masaüstündeki Chromium tarayıcılarına kurulur; diğerlerinde mağaza düğmesi yerine bağlantı kopyalanır.
  const ua = navigator.userAgent;
  const mobile = navigator.userAgentData?.mobile ?? (/Android|iPhone|iPad|iPod|Mobile/i.test(ua)
    || (/Macintosh/.test(ua) && navigator.maxTouchPoints > 1));
  if (mobile || !window.chrome) {
    $("notice").textContent = mobile ? t.mobile : t.otherBrowser;
    $("notice").hidden = false;
    $("install").hidden = true;
    $("copy-link").hidden = false;
    return;
  }

  // Sunucu, izin verilen eklenti kimliklerini sayfaya yazar; tanımlı değilse mağazadaki kimlik denenir.
  const raw = document.querySelector("main").dataset.ids || "";
  const ids = raw ? raw.split(",") : [STORE_ID];
  const send = (id, msg) => new Promise((resolve) => {
    try {
      chrome.runtime.sendMessage(id, msg, (res) => resolve(chrome.runtime.lastError ? null : res));
    } catch {
      resolve(null);
    }
  });

  // chrome.runtime bir web sayfasında yalnızca bu siteye mesaj izni veren bir eklenti kuruluyken tanımlıdır.
  // Chrome bunu sayfa açılırken ayarlar; eklenti sayfa açıkken kurulursa genellikle yenileme gerekir.
  let found = null;
  async function detect() {
    if (found || !(window.chrome && chrome.runtime && chrome.runtime.sendMessage)) return;
    for (const id of ids) {
      if ((await send(id, { type: "ping" }))?.ok) {
        found = id;
        $("step-install").hidden = true;
        $("step-join").textContent = t.stepJoinReady;
        $("install").hidden = true;
        $("reload-row").hidden = true;
        $("join").hidden = false;
        return;
      }
    }
  }
  detect();
  setInterval(detect, 3000);

  // Mağazaya gidip dönen kişiye, eklenti hâlâ görünmüyorsa sayfayı yenilemesi söylenir.
  let installClicked = false;
  $("install").addEventListener("click", () => { installClicked = true; });
  const onReturn = async () => {
    if (document.visibilityState !== "visible") return;
    await detect();
    if (installClicked && !found) $("reload-row").hidden = false;
  };
  addEventListener("focus", onReturn);
  document.addEventListener("visibilitychange", onReturn);

  $("join").onclick = async () => {
    const res = await send(found, { type: "invite", code });
    $("status").classList.toggle("error", !res?.ok);
    $("status").textContent = !res?.ok ? t.failed : res.opened ? t.sentOpened : t.sent;
  };
})();
