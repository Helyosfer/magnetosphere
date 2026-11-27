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
      safety: "Güvenli: Giriş Kick'in kendi sayfasında yapılır, şifren kimseyle paylaşılmaz. Magnetosphere'in kodu siber güvenlik odaklı yapay zekâ modelleri desteğiyle denetlenir.",
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
      safety: "Safe to join: you sign in on Kick's own page and your password is never shared. Magnetosphere's code is audited with the help of cybersecurity-focused AI models.",
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
      safety: "Seguro: inicias sesión en la propia página de Kick y tu contraseña nunca se comparte. El código de Magnetosphere se audita con el apoyo de modelos de IA especializados en ciberseguridad.",
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
      safety: "Seguro: o login é feito na própria página da Kick e sua senha nunca é compartilhada. O código do Magnetosphere é auditado com o apoio de modelos de IA focados em cibersegurança.",
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
      safety: "آمن: يتم تسجيل الدخول في صفحة Kick نفسها ولا تُشارَك كلمة مرورك أبدًا. تُدقَّق شيفرة Magnetosphere بمساعدة نماذج ذكاء اصطناعي متخصصة في الأمن السيبراني.",
    },
    de: {
      title: "Du wurdest in ein Magnetosphere-Team eingeladen",
      lead: "Sobald du beitrittst, gilt ein Bann in einem Kanal in allen Kanälen des Teams.",
      stepInstall: "Installiere die Magnetosphere-Erweiterung in Chrome.",
      stepJoin: "Komm zu dieser Seite zurück und klicke auf Team beitreten, oder kopiere den Code und füge ihn in der Erweiterung ins Feld für den Einladungscode ein.",
      stepJoinReady: "Klicke auf Team beitreten und bestätige in der Erweiterung.",
      copy: "Kopieren", copied: "Kopiert",
      install: "Im Chrome Web Store installieren", join: "Team beitreten",
      mobile: "Magnetosphere läuft in Chrome auf dem Computer und lässt sich nicht auf dem Handy installieren. Öffne diesen Link auf deinem Computer.",
      otherBrowser: "Magnetosphere funktioniert in diesem Browser nicht. Öffne diesen Link auf deinem Computer in Chrome (oder einem Chromium-Browser wie Edge oder Brave).",
      copyLink: "Link kopieren", linkCopied: "Link kopiert",
      reloadHint: "Installation fertig? Lade diese Seite neu.", reload: "Neu laden",
      sent: "Die Einladung wurde an die Erweiterung übergeben. Falls sie sich nicht geöffnet hat, klicke oben rechts in Chrome auf das Magnetosphere-Symbol; die Bestätigung wartet dort.",
      sentOpened: "Die Erweiterung ist offen; bestätige dort den Beitritt.",
      failed: "Die Einladung konnte nicht an die Erweiterung übergeben werden. Du kannst den Code kopieren und in die Erweiterung einfügen.",
      missing: "Dieser Link enthält keinen Einladungscode. Bitte die Person, die dich eingeladen hat, ihn noch einmal zu schicken.",
      safety: "Sicher: Du meldest dich auf Kicks eigener Seite an, dein Passwort wird nie weitergegeben. Der Code von Magnetosphere wird mit Unterstützung von auf Cybersicherheit spezialisierten KI-Modellen geprüft.",
    },
    fr: {
      title: "Tu es invité dans une équipe Magnetosphere",
      lead: "Une fois dans l'équipe, un ban sur une chaîne s'applique sur toutes les chaînes de l'équipe.",
      stepInstall: "Installe l'extension Magnetosphere dans Chrome.",
      stepJoin: "Reviens sur cette page et clique sur Rejoindre l'équipe, ou copie le code et colle-le dans le champ du code d'invitation de l'extension.",
      stepJoinReady: "Clique sur Rejoindre l'équipe et accepte la confirmation dans l'extension.",
      copy: "Copier", copied: "Copié",
      install: "Installer depuis le Chrome Web Store", join: "Rejoindre l'équipe",
      mobile: "Magnetosphere fonctionne dans Chrome sur ordinateur ; il ne s'installe pas sur téléphone. Ouvre ce lien sur ton ordinateur.",
      otherBrowser: "Magnetosphere ne fonctionne pas dans ce navigateur. Ouvre ce lien dans Chrome sur ton ordinateur (ou dans un navigateur basé sur Chromium comme Edge ou Brave).",
      copyLink: "Copier le lien", linkCopied: "Lien copié",
      reloadHint: "Installation terminée ? Recharge cette page.", reload: "Recharger",
      sent: "L'invitation a été transmise à l'extension. Si elle ne s'est pas ouverte, clique sur l'icône Magnetosphere en haut à droite de Chrome ; la confirmation t'attend.",
      sentOpened: "L'extension est ouverte ; confirme ton arrivée depuis celle-ci.",
      failed: "Impossible de transmettre l'invitation à l'extension. Tu peux copier le code et le coller dans l'extension.",
      missing: "Ce lien ne contient pas de code d'invitation. Demande à la personne qui t'a invité de le renvoyer.",
      safety: "En toute sécurité : tu te connectes sur la page de Kick et ton mot de passe n'est jamais partagé. Le code de Magnetosphere est audité avec l'aide de modèles d'IA spécialisés en cybersécurité.",
    },
    ru: {
      title: "Тебя пригласили в команду Magnetosphere",
      lead: "После вступления бан на одном канале действует на всех каналах команды.",
      stepInstall: "Установи расширение Magnetosphere в Chrome.",
      stepJoin: "Вернись на эту страницу и нажми «Вступить в команду» или скопируй код и вставь его в поле кода приглашения в расширении.",
      stepJoinReady: "Нажми «Вступить в команду» и подтверди в расширении.",
      copy: "Копировать", copied: "Скопировано",
      install: "Установить из Chrome Web Store", join: "Вступить в команду",
      mobile: "Magnetosphere работает в Chrome на компьютере, на телефон его не установить. Открой эту ссылку на компьютере.",
      otherBrowser: "Magnetosphere не работает в этом браузере. Открой ссылку в Chrome на компьютере (или в браузере на основе Chromium, например Edge или Brave).",
      copyLink: "Копировать ссылку", linkCopied: "Ссылка скопирована",
      reloadHint: "Установка завершена? Обнови эту страницу.", reload: "Обновить",
      sent: "Приглашение передано расширению. Если оно не открылось, нажми на значок Magnetosphere справа вверху в Chrome — там ждёт подтверждение.",
      sentOpened: "Расширение открыто; подтверди вступление там.",
      failed: "Не удалось передать приглашение расширению. Можно скопировать код и вставить его в расширение.",
      missing: "В этой ссылке нет кода приглашения. Попроси пригласившего прислать её ещё раз.",
      safety: "Безопасно: вход выполняется на странице самого Kick, пароль никому не передаётся. Код Magnetosphere проверяется с помощью ИИ-моделей, специализирующихся на кибербезопасности.",
    },
    id: {
      title: "Kamu diundang ke tim Magnetosphere",
      lead: "Setelah bergabung, ban di satu channel berlaku di semua channel tim.",
      stepInstall: "Pasang ekstensi Magnetosphere di Chrome.",
      stepJoin: "Kembali ke halaman ini dan klik Gabung ke tim, atau salin kodenya dan tempel di kolom kode undangan di ekstensi.",
      stepJoinReady: "Klik Gabung ke tim lalu terima konfirmasi di ekstensi.",
      copy: "Salin", copied: "Tersalin",
      install: "Pasang dari Chrome Web Store", join: "Gabung ke tim",
      mobile: "Magnetosphere berjalan di Chrome di komputer; tidak bisa dipasang di ponsel. Buka tautan ini di komputermu.",
      otherBrowser: "Magnetosphere tidak berfungsi di browser ini. Buka tautan ini di Chrome di komputermu (atau browser berbasis Chromium seperti Edge atau Brave).",
      copyLink: "Salin tautan", linkCopied: "Tautan tersalin",
      reloadHint: "Sudah selesai memasang? Muat ulang halaman ini.", reload: "Muat ulang",
      sent: "Undangan sudah diteruskan ke ekstensi. Kalau tidak terbuka, klik ikon Magnetosphere di kanan atas Chrome; konfirmasinya menunggu di sana.",
      sentOpened: "Ekstensi sudah terbuka; konfirmasi bergabung di sana.",
      failed: "Undangan tidak bisa diteruskan ke ekstensi. Kamu bisa menyalin kodenya dan menempelkannya di ekstensi.",
      missing: "Tautan ini tidak berisi kode undangan. Minta orang yang mengundangmu mengirimkannya lagi.",
      safety: "Aman: kamu masuk di halaman Kick sendiri dan kata sandimu tidak pernah dibagikan. Kode Magnetosphere diaudit dengan bantuan model AI yang berfokus pada keamanan siber.",
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
  $("safety").textContent = t.safety;
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
