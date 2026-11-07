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
      copy: "Kopyala", copied: "Kopyalandı",
      install: "Chrome Web Store'dan kur", join: "Ekibe katıl",
      sent: "Davet eklentiye iletildi. Açılmadıysa Chrome'un sağ üstündeki Magnetosphere simgesine tıkla; katılma onayı seni bekliyor.",
      failed: "Davet eklentiye iletilemedi. Kodu kopyalayıp eklentiye yapıştırabilirsin.",
      missing: "Bu bağlantıda davet kodu yok. Seni davet eden kişiden bağlantıyı yeniden iste.",
      doc: "Magnetosphere daveti",
    },
    en: {
      title: "You're invited to a Magnetosphere team",
      lead: "Once you join, a ban on one channel is applied on all of the team's channels.",
      stepInstall: "Install the Magnetosphere extension in Chrome.",
      stepJoin: "Come back to this page and press Join team, or copy the code and paste it into the invite code field in the extension.",
      copy: "Copy", copied: "Copied",
      install: "Install from the Chrome Web Store", join: "Join team",
      sent: "The invite was passed to the extension. If it didn't open, click the Magnetosphere icon at the top right of Chrome; the join prompt is waiting.",
      failed: "Couldn't pass the invite to the extension. You can copy the code and paste it into the extension.",
      missing: "This link has no invite code. Ask the person who invited you to send it again.",
      doc: "Magnetosphere invite",
    },
    es: {
      title: "Te invitaron a un equipo de Magnetosphere",
      lead: "Al unirte, un baneo en un canal se aplica en todos los canales del equipo.",
      stepInstall: "Instala la extensión Magnetosphere en Chrome.",
      stepJoin: "Vuelve a esta página y pulsa Unirse al equipo, o copia el código y pégalo en el campo de código de invitación de la extensión.",
      copy: "Copiar", copied: "Copiado",
      install: "Instalar desde Chrome Web Store", join: "Unirse al equipo",
      sent: "La invitación se pasó a la extensión. Si no se abrió, haz clic en el icono de Magnetosphere arriba a la derecha en Chrome; la confirmación te espera.",
      failed: "No se pudo pasar la invitación a la extensión. Puedes copiar el código y pegarlo en la extensión.",
      missing: "Este enlace no tiene código de invitación. Pide a quien te invitó que lo envíe de nuevo.",
      doc: "Invitación de Magnetosphere",
    },
    pt: {
      title: "Você foi convidado para uma equipe do Magnetosphere",
      lead: "Depois de entrar, um ban em um canal é aplicado em todos os canais da equipe.",
      stepInstall: "Instale a extensão Magnetosphere no Chrome.",
      stepJoin: "Volte a esta página e clique em Entrar na equipe, ou copie o código e cole no campo de código de convite da extensão.",
      copy: "Copiar", copied: "Copiado",
      install: "Instalar pela Chrome Web Store", join: "Entrar na equipe",
      sent: "O convite foi passado para a extensão. Se ela não abriu, clique no ícone do Magnetosphere no canto superior direito do Chrome; a confirmação está esperando.",
      failed: "Não foi possível passar o convite para a extensão. Você pode copiar o código e colar na extensão.",
      missing: "Este link não tem código de convite. Peça para quem te convidou enviar de novo.",
      doc: "Convite do Magnetosphere",
    },
    ar: {
      title: "تمت دعوتك إلى فريق في Magnetosphere",
      lead: "بعد الانضمام، يُطبَّق الحظر في قناة واحدة على جميع قنوات الفريق.",
      stepInstall: "ثبّت إضافة Magnetosphere في Chrome.",
      stepJoin: "عُد إلى هذه الصفحة واضغط «الانضمام إلى الفريق»، أو انسخ الرمز والصقه في حقل رمز الدعوة في الإضافة.",
      copy: "نسخ", copied: "تم النسخ",
      install: "التثبيت من Chrome Web Store", join: "الانضمام إلى الفريق",
      sent: "تم تمرير الدعوة إلى الإضافة. إن لم تُفتح، انقر أيقونة Magnetosphere أعلى يمين Chrome؛ تأكيد الانضمام بانتظارك.",
      failed: "تعذّر تمرير الدعوة إلى الإضافة. يمكنك نسخ الرمز ولصقه في الإضافة.",
      missing: "لا يحتوي هذا الرابط على رمز دعوة. اطلب من الشخص الذي دعاك إرساله مرة أخرى.",
      doc: "دعوة Magnetosphere",
    },
  };
  const STORE_ID = "kjbbjooackbcfeeoolkfpmdbkomjiflh";
  const lang = (navigator.languages || [navigator.language || "en"])
    .map((l) => l.slice(0, 2).toLowerCase()).find((l) => TEXT[l]) || "en";
  const t = TEXT[lang];
  const $ = (id) => document.getElementById(id);
  document.documentElement.lang = lang;
  document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
  document.title = t.doc;
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
  $("invite").hidden = false;

  $("copy").onclick = async () => {
    try {
      await navigator.clipboard.writeText(code);
      $("copy").textContent = t.copied;
      setTimeout(() => { $("copy").textContent = t.copy; }, 1500);
    } catch {
      getSelection().selectAllChildren($("code"));
    }
  };

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
  let found = null;
  async function detect() {
    if (found || !(window.chrome && chrome.runtime && chrome.runtime.sendMessage)) return;
    for (const id of ids) {
      if ((await send(id, { type: "ping" }))?.ok) {
        found = id;
        $("install").hidden = true;
        $("join").hidden = false;
        return;
      }
    }
  }
  detect();
  // Kullanıcı mağazadan kurup bu sekmeye dönünce düğme kendiliğinden değişir.
  addEventListener("focus", detect);
  setInterval(detect, 3000);

  $("join").onclick = async () => {
    const res = await send(found, { type: "invite", code });
    $("status").classList.toggle("error", !res?.ok);
    $("status").textContent = res?.ok ? t.sent : t.failed;
  };
})();
