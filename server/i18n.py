"""Kullanıcıya giden mesajların İngilizcesi.

Sunucu mesajları Türkçe yazar ve veritabanına (ban ayrıntıları, sıra kayıtları) Türkçe kaydeder.
İngilizce isteyen panele yanıt giderken metin bu tablodan çevrilir; tabloda olmayan metin
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

FIXED = {tr: en for tr, en in EN.items() if "{" not in tr}
PATTERNS = [
    (re.compile(re.sub(r"\\\{(\w+)\\\}", r"(?P<\1>.+?)", re.escape(tr))), en)
    for tr, en in EN.items() if "{" in tr
]
PART_SPLIT = re.compile(r"; (?=[\w.-]+: )")


def pick_lang(header):
    """Panel dilini Accept-Language'da tek başına "en" olarak gönderir.

    Eski paneller (0.7.x) dil göndermez; tarayıcının kendi başlığı ("en-US,en;q=0.9") gelir ve
    Türkçe arayüzde İngilizce hata çıkmasın diye bu durumda Türkçe kalınır.
    """
    return "en" if (header or "").strip().lower() == "en" else "tr"


def localize(text, lang):
    if lang != "en" or not isinstance(text, str) or not text:
        return text
    if text in FIXED:
        return FIXED[text]
    for pattern, en in PATTERNS:
        match = pattern.fullmatch(text)
        if match:
            return en.format(**{k: FIXED.get(v, v) for k, v in match.groupdict().items()})
    # Kayıtlı ayrıntılar birleşik gelir: "kanal: 403: ...; kanal2: ..." ya da "ad: Kick oturumu yenilenemedi".
    # Yalnızca "kanal: " ile başlayan parçadan bölünür; mesajın kendi içindeki "; " bölünmez.
    parts = PART_SPLIT.split(text)
    if len(parts) > 1:
        return "; ".join(localize(part, lang) for part in parts)
    head, sep, rest = text.partition(": ")
    if sep:
        return head + sep + localize(rest, lang)
    return text


def localize_payload(payload, lang):
    """Yanıttaki hata ve ayrıntı alanlarını çevirir; ad, sebep gibi kullanıcı verisine dokunmaz."""
    if lang != "en":
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
            out[key] = FIXED[value]
        else:
            out[key] = localize_payload(value, lang)
    return out
