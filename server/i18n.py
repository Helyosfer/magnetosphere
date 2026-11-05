"""Kullanıcıya giden mesajların İngilizcesi, İspanyolcası, Portekizcesi ve Arapçası.

Sunucu mesajları Türkçe yazar ve veritabanına (ban ayrıntıları, sıra kayıtları) Türkçe kaydeder.
İngilizce, İspanyolca, Portekizce ya da Arapça isteyen panele yanıt giderken metin bu tablolardan çevrilir; tabloda olmayan metin
(ör. Kick'in kendi hata mesajı) olduğu gibi kalır.
"""
import re

# Türkçe kalıp -> İngilizce kalıp. {ad} ile işaretlenen yerler iki dilde de aynı değeri taşır.
EN = {
    # yetki
    "İzleyici rolündesin; bunun için moderatör yetkisi gerekir": "You're a viewer; this needs moderator permission",
    "Bunu yalnızca ekip sahibi ve yöneticiler yapabilir": "Only the team owner and admins can do this",
    "Bunu yalnızca ekip sahibi yapabilir": "Only the team owner can do this",
    # istek
    "{label} metin olmalı": "{label} must be text",
    "Ekip adı": "Team name",
    "Davet kodu": "Invite code",
    "Ban sebebi": "Ban reason",
    "Geçersiz istek": "Invalid request",
    "İstek çok büyük": "Request too large",
    "Geçersiz JSON": "Invalid JSON",
    "Bulunamadı": "Not found",
    "Sunucuda beklenmeyen bir hata oluştu": "Something went wrong on the server",
    # oturum ve giriş
    "Oturum geçersiz": "Invalid session",
    "Oturumun süresi doldu, yeniden giriş yap": "Your session expired; log in again",
    "Geçersiz redirect adresi": "Invalid redirect address",
    "Sunucuda KICK_CLIENT_ID / KICK_CLIENT_SECRET ayarlı değil": "KICK_CLIENT_ID / KICK_CLIENT_SECRET aren't set on the server",
    "Giriş isteği geçersiz ya da süresi dolmuş": "The login request is invalid or has expired",
    "Kick girişi onaylanmadı": "Kick login wasn't approved",
    "Kick girişi tamamlanamadı; biraz sonra tekrar dene": "Couldn't finish Kick login; try again in a moment",
    "Kick hesap bilgisi alınamadı; biraz sonra tekrar dene": "Couldn't get your Kick account details; try again in a moment",
    "Çok fazla giriş denemesi, birkaç dakika sonra tekrar dene": "Too many login attempts; try again in a few minutes",
    # hız sınırları
    "Çok hızlı istek gönderiyorsun; bir dakika sonra tekrar dene": "You're sending requests too fast; try again in a minute",
    "Önceki işlemin bitmesini bekle, sonra tekrar dene": "Wait for your previous action to finish, then try again",
    # Kick
    "Geçersiz kullanıcı adı (Kick adları en fazla 25 karakterdir)": "Invalid username (Kick names are at most 25 characters)",
    "Kick oturumun yenilenemedi, yeniden giriş yap": "Couldn't refresh your Kick session; log in again",
    "Kick istek sınırına takıldı, biraz sonra tekrar dene": "Hit Kick's rate limit; try again in a moment",
    "Kick bu kullanıcı adını geçersiz buldu": "Kick says this username is invalid",
    "Kick kullanıcı sorgusu başarısız ({status})": "Kick user lookup failed ({status})",
    "'{slug}' Kick'te bulunamadı": "'{slug}' was not found on Kick",
    "Kick'e ulaşılamadı": "Couldn't reach Kick",
    "Kick oturumu geçersiz; çıkış yapıp yeniden giriş yap": "Kick session is invalid; log out and log in again",
    "bu kanalda ban yetkin yok (moderatör değilsin)": "you can't ban on this channel (you're not a moderator)",
    "kullanıcı ya da kanal Kick'te bulunamadı": "user or channel not found on Kick",
    "Kick istek sınırı; biraz sonra tekrar dene": "Kick rate limit; try again in a moment",
    "Kick istek sınırı": "Kick rate limit",
    "Kick oturumu yenilenemedi": "couldn't refresh the Kick session",
    "hata": "error",
    # ekip ve üyeler
    "Ekip bulunamadı": "Team not found",
    "Ekip adı gerekli": "Team name is required",
    "Bu sunucuda yeni ekip kurma kapalı. Ekibinden bir davet kodu isteyip katılabilirsin.":
        "Creating new teams is turned off on this server. Ask your team for an invite code to join.",
    "En fazla {n} ekip kurabilirsin; kullanmadığın bir ekibi silip tekrar dene":
        "You can create at most {n} teams; delete one you don't use and try again",
    "Yeni katılanlar moderatör ya da izleyici olarak başlayabilir": "New members can start as moderator or viewer",
    "Davet kodu geçersiz": "Invalid invite code",
    "En fazla {n} ekibe üye olabilirsin": "You can be a member of at most {n} teams",
    "Ekip sahibinin rolü değiştirilemez; sahipliği başka bir üyeye devredebilirsin":
        "The team owner's role can't be changed; you can transfer ownership to another member",
    "Üye bulunamadı": "Member not found",
    "Bu üye daha fazla ekibin sahibi olamaz": "This member can't own any more teams",
    "Geçersiz rol": "Invalid role",
    "Ekip sahibi ayrılamaz; önce sahipliği başka bir üyeye devret ya da ekibi sil":
        "The team owner can't leave; transfer ownership to another member or delete the team first",
    "Ekip sahibi çıkarılamaz": "The team owner can't be removed",
    "Yalnızca kendinden düşük yetkili üyeleri çıkarabilirsin": "You can only remove members with a lower role than yours",
    "Önce şu ekiplerin sahipliğini devret ya da ekipleri sil: {names}":
        "First transfer ownership of these teams or delete them: {names}",
    "silinmiş kullanıcı": "deleted user",
    "başka bir üye": "another member",
    # banlar
    "Ban kaydı bulunamadı": "Ban record not found",
    "Süre 1 ile 10080 dakika arasında olmalı": "Duration must be between 1 and 10080 minutes",
    "Ekip üyeleri ve ekipteki yayıncılar banlanamaz": "Team members and broadcasters on the team can't be banned",
    "Önce ekibe en az bir kanal ekle": "Add at least one channel to the team first",
    "Bu ban kaldırılmış": "This ban has already been removed",
    "Yalnızca kendi attığın banı kaldırabilirsin; diğerleri için yönetici gerekir":
        "You can only remove bans you placed; others need an admin",
    "{slug} listede {creator} tarafından banlanmış; başkasının attığı banı yalnızca sahip ve yöneticiler kaldırabilir":
        "{slug} was banned by {creator} on the list; only the owner and admins can remove someone else's ban",
    # sıra
    "Kullanıcı listesi boş": "The user list is empty",
    "Tek seferde en fazla {n} kullanıcı sıraya alınabilir": "At most {n} users can be queued at once",
    "Sıra dolu; bekleyen kayıtlar işlenince tekrar dene": "The queue is full; try again once pending entries are done",
    "Listeyi yükleyen kişi artık ekipte değil ya da ban yetkisi yok":
        "The person who uploaded the list is no longer on the team or can't ban",
}

# Türkçe kalıp -> İspanyolca kalıp. Anahtarlar EN ile aynıdır (test_app.py denetler).
ES = {
    # yetki
    "İzleyici rolündesin; bunun için moderatör yetkisi gerekir": "Eres espectador; esto requiere permiso de moderador",
    "Bunu yalnızca ekip sahibi ve yöneticiler yapabilir": "Solo el dueño del equipo y los admins pueden hacer esto",
    "Bunu yalnızca ekip sahibi yapabilir": "Solo el dueño del equipo puede hacer esto",
    # istek
    "{label} metin olmalı": "{label} debe ser texto",
    "Ekip adı": "El nombre del equipo",
    "Davet kodu": "El código de invitación",
    "Ban sebebi": "El motivo del baneo",
    "Geçersiz istek": "Solicitud no válida",
    "İstek çok büyük": "Solicitud demasiado grande",
    "Geçersiz JSON": "JSON no válido",
    "Bulunamadı": "No encontrado",
    "Sunucuda beklenmeyen bir hata oluştu": "Ocurrió un error inesperado en el servidor",
    # oturum ve giriş
    "Oturum geçersiz": "Sesión no válida",
    "Oturumun süresi doldu, yeniden giriş yap": "Tu sesión expiró; vuelve a iniciar sesión",
    "Geçersiz redirect adresi": "Dirección de redirección no válida",
    "Sunucuda KICK_CLIENT_ID / KICK_CLIENT_SECRET ayarlı değil": "KICK_CLIENT_ID / KICK_CLIENT_SECRET no están configurados en el servidor",
    "Giriş isteği geçersiz ya da süresi dolmuş": "La solicitud de inicio de sesión no es válida o expiró",
    "Kick girişi onaylanmadı": "No se aprobó el inicio de sesión en Kick",
    "Kick girişi tamamlanamadı; biraz sonra tekrar dene": "No se pudo completar el inicio de sesión en Kick; inténtalo de nuevo en un rato",
    "Kick hesap bilgisi alınamadı; biraz sonra tekrar dene": "No se pudieron obtener los datos de tu cuenta de Kick; inténtalo de nuevo en un rato",
    "Çok fazla giriş denemesi, birkaç dakika sonra tekrar dene": "Demasiados intentos de inicio de sesión; inténtalo de nuevo en unos minutos",
    # hız sınırları
    "Çok hızlı istek gönderiyorsun; bir dakika sonra tekrar dene": "Estás enviando solicitudes muy rápido; inténtalo de nuevo en un minuto",
    "Önceki işlemin bitmesini bekle, sonra tekrar dene": "Espera a que termine tu acción anterior y vuelve a intentarlo",
    # Kick
    "Geçersiz kullanıcı adı (Kick adları en fazla 25 karakterdir)": "Usuario no válido (los nombres de Kick tienen como máximo 25 caracteres)",
    "Kick oturumun yenilenemedi, yeniden giriş yap": "No se pudo renovar tu sesión de Kick; vuelve a iniciar sesión",
    "Kick istek sınırına takıldı, biraz sonra tekrar dene": "Se alcanzó el límite de solicitudes de Kick; inténtalo de nuevo en un rato",
    "Kick bu kullanıcı adını geçersiz buldu": "Kick considera que este usuario no es válido",
    "Kick kullanıcı sorgusu başarısız ({status})": "Falló la búsqueda del usuario en Kick ({status})",
    "'{slug}' Kick'te bulunamadı": "'{slug}' no existe en Kick",
    "Kick'e ulaşılamadı": "No se pudo contactar con Kick",
    "Kick oturumu geçersiz; çıkış yapıp yeniden giriş yap": "La sesión de Kick no es válida; cierra sesión y vuelve a iniciarla",
    "bu kanalda ban yetkin yok (moderatör değilsin)": "no puedes banear en este canal (no eres moderador)",
    "kullanıcı ya da kanal Kick'te bulunamadı": "el usuario o el canal no existe en Kick",
    "Kick istek sınırı; biraz sonra tekrar dene": "límite de solicitudes de Kick; inténtalo de nuevo en un rato",
    "Kick istek sınırı": "límite de solicitudes de Kick",
    "Kick oturumu yenilenemedi": "no se pudo renovar la sesión de Kick",
    "hata": "error",
    # ekip ve üyeler
    "Ekip bulunamadı": "Equipo no encontrado",
    "Ekip adı gerekli": "El nombre del equipo es obligatorio",
    "Bu sunucuda yeni ekip kurma kapalı. Ekibinden bir davet kodu isteyip katılabilirsin.":
        "Crear equipos nuevos está desactivado en este servidor. Pide a tu equipo un código de invitación para unirte.",
    "En fazla {n} ekip kurabilirsin; kullanmadığın bir ekibi silip tekrar dene":
        "Puedes crear como máximo {n} equipos; elimina uno que no uses y vuelve a intentarlo",
    "Yeni katılanlar moderatör ya da izleyici olarak başlayabilir": "Los nuevos miembros pueden empezar como moderador o espectador",
    "Davet kodu geçersiz": "Código de invitación no válido",
    "En fazla {n} ekibe üye olabilirsin": "Puedes ser miembro de {n} equipos como máximo",
    "Ekip sahibinin rolü değiştirilemez; sahipliği başka bir üyeye devredebilirsin":
        "No se puede cambiar el rol del dueño del equipo; puedes transferir la propiedad a otro miembro",
    "Üye bulunamadı": "Miembro no encontrado",
    "Bu üye daha fazla ekibin sahibi olamaz": "Este miembro no puede ser dueño de más equipos",
    "Geçersiz rol": "Rol no válido",
    "Ekip sahibi ayrılamaz; önce sahipliği başka bir üyeye devret ya da ekibi sil":
        "El dueño del equipo no puede salir; primero transfiere la propiedad a otro miembro o elimina el equipo",
    "Ekip sahibi çıkarılamaz": "No se puede quitar al dueño del equipo",
    "Yalnızca kendinden düşük yetkili üyeleri çıkarabilirsin": "Solo puedes quitar a miembros con un rol inferior al tuyo",
    "Önce şu ekiplerin sahipliğini devret ya da ekipleri sil: {names}":
        "Primero transfiere la propiedad de estos equipos o elimínalos: {names}",
    "silinmiş kullanıcı": "usuario eliminado",
    "başka bir üye": "otro miembro",
    # banlar
    "Ban kaydı bulunamadı": "Registro de baneo no encontrado",
    "Süre 1 ile 10080 dakika arasında olmalı": "La duración debe estar entre 1 y 10080 minutos",
    "Ekip üyeleri ve ekipteki yayıncılar banlanamaz": "No se puede banear a miembros del equipo ni a streamers del equipo",
    "Önce ekibe en az bir kanal ekle": "Primero agrega al menos un canal al equipo",
    "Bu ban kaldırılmış": "Este baneo ya se quitó",
    "Yalnızca kendi attığın banı kaldırabilirsin; diğerleri için yönetici gerekir":
        "Solo puedes quitar los baneos que hiciste tú; para los demás se necesita un admin",
    "{slug} listede {creator} tarafından banlanmış; başkasının attığı banı yalnızca sahip ve yöneticiler kaldırabilir":
        "{creator} baneó a {slug} en la lista; solo el dueño y los admins pueden quitar el baneo de otra persona",
    # sıra
    "Kullanıcı listesi boş": "La lista de usuarios está vacía",
    "Tek seferde en fazla {n} kullanıcı sıraya alınabilir": "Se pueden poner en cola como máximo {n} usuarios a la vez",
    "Sıra dolu; bekleyen kayıtlar işlenince tekrar dene": "La cola está llena; vuelve a intentarlo cuando se procesen los pendientes",
    "Listeyi yükleyen kişi artık ekipte değil ya da ban yetkisi yok":
        "Quien subió la lista ya no está en el equipo o no puede banear",
}

# Türkçe kalıp -> Portekizce (Brezilya) kalıp. Anahtarlar EN ile aynıdır (test_app.py denetler).
PT = {
    # yetki
    "İzleyici rolündesin; bunun için moderatör yetkisi gerekir": "Você é espectador; isso exige permissão de moderador",
    "Bunu yalnızca ekip sahibi ve yöneticiler yapabilir": "Só o dono da equipe e os admins podem fazer isso",
    "Bunu yalnızca ekip sahibi yapabilir": "Só o dono da equipe pode fazer isso",
    # istek
    "{label} metin olmalı": "{label} precisa ser texto",
    "Ekip adı": "O nome da equipe",
    "Davet kodu": "O código de convite",
    "Ban sebebi": "O motivo do ban",
    "Geçersiz istek": "Solicitação inválida",
    "İstek çok büyük": "Solicitação grande demais",
    "Geçersiz JSON": "JSON inválido",
    "Bulunamadı": "Não encontrado",
    "Sunucuda beklenmeyen bir hata oluştu": "Ocorreu um erro inesperado no servidor",
    # oturum ve giriş
    "Oturum geçersiz": "Sessão inválida",
    "Oturumun süresi doldu, yeniden giriş yap": "Sua sessão expirou; entre de novo",
    "Geçersiz redirect adresi": "Endereço de redirecionamento inválido",
    "Sunucuda KICK_CLIENT_ID / KICK_CLIENT_SECRET ayarlı değil": "KICK_CLIENT_ID / KICK_CLIENT_SECRET não estão configurados no servidor",
    "Giriş isteği geçersiz ya da süresi dolmuş": "A solicitação de login é inválida ou expirou",
    "Kick girişi onaylanmadı": "O login na Kick não foi aprovado",
    "Kick girişi tamamlanamadı; biraz sonra tekrar dene": "Não foi possível concluir o login na Kick; tente de novo daqui a pouco",
    "Kick hesap bilgisi alınamadı; biraz sonra tekrar dene": "Não foi possível obter os dados da sua conta da Kick; tente de novo daqui a pouco",
    "Çok fazla giriş denemesi, birkaç dakika sonra tekrar dene": "Tentativas de login demais; tente de novo em alguns minutos",
    # hız sınırları
    "Çok hızlı istek gönderiyorsun; bir dakika sonra tekrar dene": "Você está enviando solicitações rápido demais; tente de novo em um minuto",
    "Önceki işlemin bitmesini bekle, sonra tekrar dene": "Espere a ação anterior terminar e tente de novo",
    # Kick
    "Geçersiz kullanıcı adı (Kick adları en fazla 25 karakterdir)": "Usuário inválido (nomes da Kick têm no máximo 25 caracteres)",
    "Kick oturumun yenilenemedi, yeniden giriş yap": "Não foi possível renovar sua sessão da Kick; entre de novo",
    "Kick istek sınırına takıldı, biraz sonra tekrar dene": "O limite de solicitações da Kick foi atingido; tente de novo daqui a pouco",
    "Kick bu kullanıcı adını geçersiz buldu": "A Kick considera este usuário inválido",
    "Kick kullanıcı sorgusu başarısız ({status})": "A busca do usuário na Kick falhou ({status})",
    "'{slug}' Kick'te bulunamadı": "'{slug}' não existe na Kick",
    "Kick'e ulaşılamadı": "Não foi possível acessar a Kick",
    "Kick oturumu geçersiz; çıkış yapıp yeniden giriş yap": "A sessão da Kick é inválida; saia e entre de novo",
    "bu kanalda ban yetkin yok (moderatör değilsin)": "você não pode banir neste canal (não é moderador)",
    "kullanıcı ya da kanal Kick'te bulunamadı": "o usuário ou o canal não existe na Kick",
    "Kick istek sınırı; biraz sonra tekrar dene": "limite de solicitações da Kick; tente de novo daqui a pouco",
    "Kick istek sınırı": "limite de solicitações da Kick",
    "Kick oturumu yenilenemedi": "não foi possível renovar a sessão da Kick",
    "hata": "erro",
    # ekip ve üyeler
    "Ekip bulunamadı": "Equipe não encontrada",
    "Ekip adı gerekli": "O nome da equipe é obrigatório",
    "Bu sunucuda yeni ekip kurma kapalı. Ekibinden bir davet kodu isteyip katılabilirsin.":
        "Criar equipes novas está desativado neste servidor. Peça um código de convite à sua equipe para entrar.",
    "En fazla {n} ekip kurabilirsin; kullanmadığın bir ekibi silip tekrar dene":
        "Você pode criar no máximo {n} equipes; exclua uma que não usa e tente de novo",
    "Yeni katılanlar moderatör ya da izleyici olarak başlayabilir": "Novos membros podem começar como moderador ou espectador",
    "Davet kodu geçersiz": "Código de convite inválido",
    "En fazla {n} ekibe üye olabilirsin": "Você pode participar de no máximo {n} equipes",
    "Ekip sahibinin rolü değiştirilemez; sahipliği başka bir üyeye devredebilirsin":
        "O cargo do dono da equipe não pode ser alterado; você pode transferir a posse para outro membro",
    "Üye bulunamadı": "Membro não encontrado",
    "Bu üye daha fazla ekibin sahibi olamaz": "Este membro não pode ser dono de mais equipes",
    "Geçersiz rol": "Cargo inválido",
    "Ekip sahibi ayrılamaz; önce sahipliği başka bir üyeye devret ya da ekibi sil":
        "O dono da equipe não pode sair; primeiro transfira a posse para outro membro ou exclua a equipe",
    "Ekip sahibi çıkarılamaz": "O dono da equipe não pode ser removido",
    "Yalnızca kendinden düşük yetkili üyeleri çıkarabilirsin": "Você só pode remover membros com cargo abaixo do seu",
    "Önce şu ekiplerin sahipliğini devret ya da ekipleri sil: {names}":
        "Primeiro transfira a posse destas equipes ou exclua-as: {names}",
    "silinmiş kullanıcı": "usuário excluído",
    "başka bir üye": "outro membro",
    # banlar
    "Ban kaydı bulunamadı": "Registro de ban não encontrado",
    "Süre 1 ile 10080 dakika arasında olmalı": "A duração precisa estar entre 1 e 10080 minutos",
    "Ekip üyeleri ve ekipteki yayıncılar banlanamaz": "Membros da equipe e streamers da equipe não podem ser banidos",
    "Önce ekibe en az bir kanal ekle": "Primeiro adicione pelo menos um canal à equipe",
    "Bu ban kaldırılmış": "Este ban já foi removido",
    "Yalnızca kendi attığın banı kaldırabilirsin; diğerleri için yönetici gerekir":
        "Você só pode remover os bans que você fez; para os outros é preciso um admin",
    "{slug} listede {creator} tarafından banlanmış; başkasının attığı banı yalnızca sahip ve yöneticiler kaldırabilir":
        "{slug} foi banido por {creator} na lista; só o dono e os admins podem remover o ban de outra pessoa",
    # sıra
    "Kullanıcı listesi boş": "A lista de usuários está vazia",
    "Tek seferde en fazla {n} kullanıcı sıraya alınabilir": "No máximo {n} usuários podem entrar na fila de uma vez",
    "Sıra dolu; bekleyen kayıtlar işlenince tekrar dene": "A fila está cheia; tente de novo quando os pendentes forem processados",
    "Listeyi yükleyen kişi artık ekipte değil ya da ban yetkisi yok":
        "Quem enviou a lista não está mais na equipe ou não pode banir",
}

# Türkçe kalıp -> Arapça kalıp. Anahtarlar EN ile aynıdır (test_app.py denetler).
AR = {
    # yetki
    "İzleyici rolündesin; bunun için moderatör yetkisi gerekir": "دورك مشاهد؛ يتطلب هذا صلاحية مشرف",
    "Bunu yalnızca ekip sahibi ve yöneticiler yapabilir": "لا يمكن القيام بهذا إلا لمالك الفريق والمديرين",
    "Bunu yalnızca ekip sahibi yapabilir": "لا يمكن القيام بهذا إلا لمالك الفريق",
    # istek
    "{label} metin olmalı": "يجب أن يكون {label} نصًا",
    "Ekip adı": "اسم الفريق",
    "Davet kodu": "رمز الدعوة",
    "Ban sebebi": "سبب الحظر",
    "Geçersiz istek": "طلب غير صالح",
    "İstek çok büyük": "الطلب كبير جدًا",
    "Geçersiz JSON": "JSON غير صالح",
    "Bulunamadı": "غير موجود",
    "Sunucuda beklenmeyen bir hata oluştu": "حدث خطأ غير متوقع في الخادم",
    # oturum ve giriş
    "Oturum geçersiz": "الجلسة غير صالحة",
    "Oturumun süresi doldu, yeniden giriş yap": "انتهت صلاحية جلستك؛ سجّل الدخول مجددًا",
    "Geçersiz redirect adresi": "عنوان إعادة التوجيه غير صالح",
    "Sunucuda KICK_CLIENT_ID / KICK_CLIENT_SECRET ayarlı değil": "لم يُضبط KICK_CLIENT_ID / KICK_CLIENT_SECRET على الخادم",
    "Giriş isteği geçersiz ya da süresi dolmuş": "طلب تسجيل الدخول غير صالح أو منتهي الصلاحية",
    "Kick girişi onaylanmadı": "لم تتم الموافقة على تسجيل الدخول عبر Kick",
    "Kick girişi tamamlanamadı; biraz sonra tekrar dene": "تعذّر إكمال تسجيل الدخول عبر Kick؛ حاول مجددًا بعد قليل",
    "Kick hesap bilgisi alınamadı; biraz sonra tekrar dene": "تعذّر الحصول على بيانات حسابك في Kick؛ حاول مجددًا بعد قليل",
    "Çok fazla giriş denemesi, birkaç dakika sonra tekrar dene": "محاولات تسجيل دخول كثيرة جدًا؛ حاول مجددًا بعد بضع دقائق",
    # hız sınırları
    "Çok hızlı istek gönderiyorsun; bir dakika sonra tekrar dene": "ترسل الطلبات بسرعة كبيرة؛ حاول مجددًا بعد دقيقة",
    "Önceki işlemin bitmesini bekle, sonra tekrar dene": "انتظر حتى تنتهي العملية السابقة ثم حاول مجددًا",
    # Kick
    "Geçersiz kullanıcı adı (Kick adları en fazla 25 karakterdir)": "اسم مستخدم غير صالح (أسماء Kick لا تتجاوز 25 حرفًا)",
    "Kick oturumun yenilenemedi, yeniden giriş yap": "تعذّر تجديد جلستك في Kick؛ سجّل الدخول مجددًا",
    "Kick istek sınırına takıldı, biraz sonra tekrar dene": "تم بلوغ حد طلبات Kick؛ حاول مجددًا بعد قليل",
    "Kick bu kullanıcı adını geçersiz buldu": "يعتبر Kick اسم المستخدم هذا غير صالح",
    "Kick kullanıcı sorgusu başarısız ({status})": "فشل البحث عن المستخدم في Kick ({status})",
    "'{slug}' Kick'te bulunamadı": "'{slug}' غير موجود على Kick",
    "Kick'e ulaşılamadı": "تعذّر الوصول إلى Kick",
    "Kick oturumu geçersiz; çıkış yapıp yeniden giriş yap": "جلسة Kick غير صالحة؛ سجّل الخروج ثم الدخول مجددًا",
    "bu kanalda ban yetkin yok (moderatör değilsin)": "لا يمكنك الحظر في هذه القناة (لست مشرفًا)",
    "kullanıcı ya da kanal Kick'te bulunamadı": "المستخدم أو القناة غير موجود على Kick",
    "Kick istek sınırı; biraz sonra tekrar dene": "حد طلبات Kick؛ حاول مجددًا بعد قليل",
    "Kick istek sınırı": "حد طلبات Kick",
    "Kick oturumu yenilenemedi": "تعذّر تجديد جلسة Kick",
    "hata": "خطأ",
    # ekip ve üyeler
    "Ekip bulunamadı": "الفريق غير موجود",
    "Ekip adı gerekli": "اسم الفريق مطلوب",
    "Bu sunucuda yeni ekip kurma kapalı. Ekibinden bir davet kodu isteyip katılabilirsin.":
        "إنشاء فرق جديدة معطّل على هذا الخادم. اطلب من فريقك رمز دعوة للانضمام.",
    "En fazla {n} ekip kurabilirsin; kullanmadığın bir ekibi silip tekrar dene":
        "يمكنك إنشاء {n} فرق كحد أقصى؛ احذف فريقًا لا تستخدمه ثم حاول مجددًا",
    "Yeni katılanlar moderatör ya da izleyici olarak başlayabilir": "يمكن للأعضاء الجدد البدء مشرفين أو مشاهدين",
    "Davet kodu geçersiz": "رمز الدعوة غير صالح",
    "En fazla {n} ekibe üye olabilirsin": "يمكنك أن تكون عضوًا في {n} فرق كحد أقصى",
    "Ekip sahibinin rolü değiştirilemez; sahipliği başka bir üyeye devredebilirsin":
        "لا يمكن تغيير دور مالك الفريق؛ يمكنك نقل الملكية إلى عضو آخر",
    "Üye bulunamadı": "العضو غير موجود",
    "Bu üye daha fazla ekibin sahibi olamaz": "لا يمكن لهذا العضو امتلاك المزيد من الفرق",
    "Geçersiz rol": "دور غير صالح",
    "Ekip sahibi ayrılamaz; önce sahipliği başka bir üyeye devret ya da ekibi sil":
        "لا يمكن لمالك الفريق المغادرة؛ انقل الملكية إلى عضو آخر أو احذف الفريق أولًا",
    "Ekip sahibi çıkarılamaz": "لا يمكن إزالة مالك الفريق",
    "Yalnızca kendinden düşük yetkili üyeleri çıkarabilirsin": "يمكنك إزالة الأعضاء ذوي الدور الأدنى منك فقط",
    "Önce şu ekiplerin sahipliğini devret ya da ekipleri sil: {names}":
        "انقل ملكية هذه الفرق أو احذفها أولًا: {names}",
    "silinmiş kullanıcı": "مستخدم محذوف",
    "başka bir üye": "عضو آخر",
    # banlar
    "Ban kaydı bulunamadı": "سجل الحظر غير موجود",
    "Süre 1 ile 10080 dakika arasında olmalı": "يجب أن تكون المدة بين 1 و10080 دقيقة",
    "Ekip üyeleri ve ekipteki yayıncılar banlanamaz": "لا يمكن حظر أعضاء الفريق وأصحاب القنوات في الفريق",
    "Önce ekibe en az bir kanal ekle": "أضف قناة واحدة على الأقل إلى الفريق أولًا",
    "Bu ban kaldırılmış": "رُفع هذا الحظر بالفعل",
    "Yalnızca kendi attığın banı kaldırabilirsin; diğerleri için yönetici gerekir":
        "يمكنك رفع الحظر الذي وضعته بنفسك فقط؛ غير ذلك يتطلب مديرًا",
    "{slug} listede {creator} tarafından banlanmış; başkasının attığı banı yalnızca sahip ve yöneticiler kaldırabilir":
        "حظر {creator} المستخدم {slug} في القائمة؛ لا يرفع حظر الآخرين إلا المالك والمديرون",
    # sıra
    "Kullanıcı listesi boş": "قائمة المستخدمين فارغة",
    "Tek seferde en fazla {n} kullanıcı sıraya alınabilir": "يمكن إضافة {n} مستخدم كحد أقصى إلى الطابور في المرة الواحدة",
    "Sıra dolu; bekleyen kayıtlar işlenince tekrar dene": "الطابور ممتلئ؛ حاول مجددًا بعد معالجة الإدخالات المنتظرة",
    "Listeyi yükleyen kişi artık ekipte değil ya da ban yetkisi yok":
        "الشخص الذي رفع القائمة لم يعد في الفريق أو لا يملك صلاحية الحظر",
}

TABLES = {"en": EN, "es": ES, "pt": PT, "ar": AR}
LANGS = tuple(TABLES)
FIXED = {lang: {tr: out for tr, out in table.items() if "{" not in tr} for lang, table in TABLES.items()}
PATTERNS = {
    lang: [
        (re.compile(re.sub(r"\\\{(\w+)\\\}", r"(?P<\1>.+?)", re.escape(tr))), out)
        for tr, out in table.items() if "{" in tr
    ]
    for lang, table in TABLES.items()
}
PART_SPLIT = re.compile(r"; (?=[\w.-]+: )")


def pick_lang(header):
    """Panel dilini Accept-Language'da tek başına ("en", "es", "pt", "ar") gönderir.

    Eski paneller (0.7.x) dil göndermez; tarayıcının kendi başlığı ("en-US,en;q=0.9") gelir ve
    Türkçe arayüzde başka dilde hata çıkmasın diye bu durumda Türkçe kalınır.
    """
    lang = (header or "").strip().lower()
    return lang if lang in LANGS else "tr"


# Bundan uzun metin çevrilmeden döner; sınır, beklenmedik uzunlukta bir metnin yanıtı yavaşlatmasını önler.
# Gerçek mesajlar çok daha kısadır: kanal başına ayrıntı ~240 karakter (Kick mesajı 200 karakterle sınırlı),
# birleşik ayrıntı en fazla 50 kanal kadar.
MAX_LOCALIZE = 20000      # "kanal: ...; kanal2: ..." gibi birleşik metnin tamamı
MAX_LOCALIZE_PART = 1000  # bölündükten sonraki tek parça


def _translate(text, fixed, patterns):
    """Metnin tamamı bilinen bir mesajsa çevirisini, değilse None döndürür."""
    if text in fixed:
        return fixed[text]
    for pattern, out in patterns:
        match = pattern.fullmatch(text)
        if match:
            return out.format(**{k: fixed.get(v, v) for k, v in match.groupdict().items()})
    return None


def localize(text, lang):
    if lang not in LANGS or not isinstance(text, str) or not text or len(text) > MAX_LOCALIZE:
        return text
    fixed, patterns = FIXED[lang], PATTERNS[lang]
    # Kayıtlı ayrıntılar birleşik gelir: "kanal: 403: ...; kanal2: ..." ya da "ad: Kick oturumu yenilenemedi".
    # Yalnızca "kanal: " ile başlayan parçadan bölünür; mesajın kendi içindeki "; " bölünmez.
    short = len(text) <= MAX_LOCALIZE_PART
    if (whole := _translate(text, fixed, patterns) if short else None) is None:
        parts = PART_SPLIT.split(text)
        if len(parts) > 1:
            return "; ".join(localize(part, lang) for part in parts)
    # Baştaki "ad: " ya da "403: " önekleri tek tek atlanır. Özyineleme yerine döngü: çok sayıda ": " içeren
    # bir metin yığını taşırıp yanıtı 500'e düşürmesin. Bölünmüş parçalarda bölünecek yer kalmaz,
    # bu yüzden yukarıdaki özyineleme en fazla bir kat derinleşir.
    if not short:
        return text
    prefix = ""
    while True:
        hit = whole if whole is not None else _translate(text, fixed, patterns)
        if hit is not None:
            return prefix + hit
        head, sep, rest = text.partition(": ")
        if not sep:
            return prefix + text
        prefix, text, whole = prefix + head + sep, rest, None


def localize_payload(payload, lang):
    """Yanıttaki hata ve ayrıntı alanlarını çevirir; ad, sebep gibi kullanıcı verisine dokunmaz."""
    if lang not in LANGS:
        return payload
    if isinstance(payload, list):
        return [localize_payload(item, lang) for item in payload]
    if not isinstance(payload, dict):
        return payload
    out = {}
    for key, value in payload.items():
        if key in ("error", "detail"):
            out[key] = localize(value, lang)
        elif key in ("created_by", "name", "creator") and value == "silinmiş kullanıcı":
            out[key] = FIXED[lang][value]
        else:
            out[key] = localize_payload(value, lang)
    return out
