"""Kick ortak ban listesi sunucusu. Yalnızca standart kütüphane kullanır.

Çalıştırma: python app.py   (ayarlar için .env.example dosyasına bakın)
"""
import base64
import contextlib
import hashlib
import json
import os
import re
import secrets
import sqlite3
import threading
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))


def load_dotenv(path):
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())


load_dotenv(os.path.join(HERE, ".env"))

CFG = {
    "client_id": os.environ.get("KICK_CLIENT_ID", ""),
    "client_secret": os.environ.get("KICK_CLIENT_SECRET", ""),
    # Kick uygulamasına kayıtlı redirect URL'i: {public_url}/auth/callback
    "public_url": os.environ.get("PUBLIC_URL", "http://localhost:8787").rstrip("/"),
    "host": os.environ.get("HOST", "127.0.0.1"),
    "port": int(os.environ.get("PORT", "8787")),
    "db": os.environ.get("DB_PATH", os.path.join(HERE, "crossban.db")),
    "kick_id": os.environ.get("KICK_ID_BASE", "https://id.kick.com").rstrip("/"),
    "kick_api": os.environ.get("KICK_API_BASE", "https://api.kick.com").rstrip("/"),
    # Boşsa her extension kimliği kabul edilir; doluysa virgülle ayrılmış kimlikler.
    "extension_ids": [x.strip() for x in os.environ.get("ALLOWED_EXTENSION_IDS", "").split(",") if x.strip()],
    # Boşsa giriş yapan herkes ekip oluşturabilir; doluysa yalnızca bu Kick kullanıcı kimlikleri.
    # Davet koduyla ekibe katılmak her durumda açıktır.
    "team_creators": {int(x) for x in os.environ.get("ALLOWED_TEAM_CREATORS", "").split(",") if x.strip()},
    # Kick tokenlarını veritabanında şifrelemek için anahtar (Fernet). Boşsa tokenlar düz metin kalır.
    "token_key": os.environ.get("TOKEN_ENCRYPTION_KEY", ""),
    # Sırayı aynı anda işleyen işçi sayısı; Kick istek sınırına takılırsa düşürün.
    "queue_workers": int(os.environ.get("QUEUE_WORKERS", "4")),
    # Kick API'sine saniyede atılacak istek sayısının başlangıç ve üst sınırı.
    # Kick 429 dönerse hız kendiliğinden düşer, sorun çıkmadıkça yavaşça yükselir.
    "kick_rps": float(os.environ.get("KICK_REQUESTS_PER_SECOND", "1")),
    "kick_rps_max": float(os.environ.get("KICK_REQUESTS_PER_SECOND_MAX", "5")),
}

VERSION = "0.5.1"
SCOPES = "user:read channel:read moderation:ban"
# Chrome'un getRedirectURL() adresi; yolda yalnızca güvenli karakterler (satır sonu ve boşluk yok).
REDIRECT_RE = re.compile(r"https://([a-p]{32})\.chromiumapp\.org/[A-Za-z0-9._~/-]*")
MAX_IMPORT = 5000
MAX_BODY_BYTES = 1_000_000
MAX_QUEUE_PER_TEAM = 20_000   # bir ekibin sırada bekleyebilecek en fazla kaydı
LOGIN_LIMIT = 30              # aynı adresten LOGIN_WINDOW saniyede başlatılabilecek giriş sayısı
LOGIN_WINDOW = 600
SESSION_TTL = 30 * 24 * 3600   # son kullanımdan sonra oturumun geçerli kaldığı süre
LOOKUP_BATCH = 50      # Kick tek sorguda en fazla 50 kanal döndürür
MAX_PARALLEL_CHANNELS = 8
# Herkese açık sunucuda tek bir hesabın kaynakları tüketmemesi için sınırlar.
MAX_TEAMS_OWNED = 10          # bir kullanıcının sahibi olabileceği ekip sayısı
MAX_TEAMS_JOINED = 50         # bir kullanıcının üyesi olabileceği ekip sayısı
MAX_CHANNELS_PER_TEAM = 50    # her ban, kanal sayısı kadar Kick isteğine dönüşür
MAX_MEMBERS_PER_TEAM = 200
MAX_KICK_CALLS_PER_USER = 2   # bir kullanıcının aynı anda Kick'e giden ban/kaldırma/kanal işlemi
REQUEST_LIMIT = 300           # bir kullanıcının REQUEST_WINDOW saniyede atabileceği istek sayısı
REQUEST_WINDOW = 60

# Ekip içi roller, yetkiye göre sıralı. Sahiplik teams.owner_id'den, diğerleri members.role'dan okunur.
#   viewer (izleyici): ortak listeyi görür
#   mod (moderatör):   ban atar, tekrar dener, kendi attığı banı kaldırır
#   admin (yönetici):  herkesin banını kaldırır, kanalları ve davet kodunu yönetir, üye çıkarır
#   owner (sahip):     rolleri ve ekip ayarlarını yönetir, sahipliği devreder, ekibi siler
ROLES = {"viewer": 0, "mod": 1, "admin": 2, "owner": 3}
ASSIGNABLE = ("viewer", "mod", "admin")
NEED_MESSAGE = {
    "mod": "İzleyici rolündesin; bunun için moderatör yetkisi gerekir",
    "admin": "Bunu yalnızca ekip sahibi ve yöneticiler yapabilir",
    "owner": "Bunu yalnızca ekip sahibi yapabilir",
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,          -- Kick user_id
    name TEXT NOT NULL,
    access_token TEXT NOT NULL,
    refresh_token TEXT NOT NULL,
    expires_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    created_at INTEGER NOT NULL,
    last_used INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS oauth_states (
    state TEXT PRIMARY KEY,
    verifier TEXT NOT NULL,
    redirect TEXT NOT NULL,
    created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS teams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    invite_code TEXT NOT NULL UNIQUE,
    owner_id INTEGER NOT NULL REFERENCES users(id),
    join_role TEXT NOT NULL DEFAULT 'mod'      -- davet koduyla katılanın rolü: mod | viewer
);
CREATE TABLE IF NOT EXISTS members (
    team_id INTEGER NOT NULL REFERENCES teams(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    role TEXT NOT NULL DEFAULT 'mod',          -- viewer | mod | admin (sahip için yok sayılır)
    lend INTEGER NOT NULL DEFAULT 0,           -- 1: ekip, bu üyenin kanalında onun yayıncı yetkisini kullanabilir
    PRIMARY KEY (team_id, user_id)
);
CREATE TABLE IF NOT EXISTS channels (
    team_id INTEGER NOT NULL REFERENCES teams(id),
    broadcaster_id INTEGER NOT NULL,
    slug TEXT NOT NULL,
    PRIMARY KEY (team_id, broadcaster_id)
);
CREATE TABLE IF NOT EXISTS bans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id INTEGER NOT NULL REFERENCES teams(id),
    target_id INTEGER NOT NULL,
    target_name TEXT NOT NULL,
    reason TEXT NOT NULL,
    duration INTEGER,                -- dakika; NULL = kalıcı
    created_by INTEGER NOT NULL REFERENCES users(id),
    created_at INTEGER NOT NULL,
    revoked_by INTEGER REFERENCES users(id),
    revoked_at INTEGER
);
CREATE TABLE IF NOT EXISTS ban_results (
    ban_id INTEGER NOT NULL REFERENCES bans(id),
    broadcaster_id INTEGER NOT NULL,
    status TEXT NOT NULL,            -- ok | failed | unbanned | unban_failed
    detail TEXT NOT NULL,
    via TEXT NOT NULL,               -- mod | broadcaster
    updated_at INTEGER NOT NULL,
    PRIMARY KEY (ban_id, broadcaster_id)
);
CREATE TABLE IF NOT EXISTS queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id INTEGER NOT NULL REFERENCES teams(id),
    target_name TEXT NOT NULL,
    reason TEXT NOT NULL,
    duration INTEGER,
    created_by INTEGER NOT NULL REFERENCES users(id),
    status TEXT NOT NULL DEFAULT 'pending',  -- pending | done | partial | notfound | rejected | error
    detail TEXT NOT NULL DEFAULT '',
    attempts INTEGER NOT NULL DEFAULT 0,
    retry_at INTEGER NOT NULL DEFAULT 0,
    created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS queue_pending ON queue (status, id);
"""


def connect():
    db = sqlite3.connect(CFG["db"], isolation_level=None, timeout=30)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA foreign_keys=ON")
    return db


def init_db():
    db = connect()
    db.executescript(SCHEMA)
    # Eski veritabanları: oturumlara son kullanım zamanı eklenir, açık oturumlar korunur.
    if "last_used" not in [c["name"] for c in db.execute("PRAGMA table_info(sessions)")]:
        db.execute("ALTER TABLE sessions ADD COLUMN last_used INTEGER NOT NULL DEFAULT 0")
    db.execute("UPDATE sessions SET last_used = ? WHERE last_used = 0", (int(time.time()),))
    # Roller ve yetki paylaşımı öncesi veritabanları. O sürümde ekipteki her yayıncının yetkisi
    # kendiliğinden kullanılıyordu; mevcut üyeliklerde bu davranış korunur, yeni katılanlar kendisi açar.
    if "role" not in [c["name"] for c in db.execute("PRAGMA table_info(members)")]:
        db.execute("ALTER TABLE members ADD COLUMN role TEXT NOT NULL DEFAULT 'mod'")
        db.execute("ALTER TABLE members ADD COLUMN lend INTEGER NOT NULL DEFAULT 0")
        db.execute("UPDATE members SET lend = 1")
    if "join_role" not in [c["name"] for c in db.execute("PRAGMA table_info(teams)")]:
        db.execute("ALTER TABLE teams ADD COLUMN join_role TEXT NOT NULL DEFAULT 'mod'")
    # Anahtar tanımlıysa düz metin kalmış tokenlar şifrelenir.
    if fernet():
        for user in db.execute("SELECT id, access_token, refresh_token FROM users").fetchall():
            if not user["access_token"].startswith(SEALED) or not user["refresh_token"].startswith(SEALED):
                db.execute("UPDATE users SET access_token = ?, refresh_token = ? WHERE id = ?",
                           (seal(unseal(user["access_token"])), seal(unseal(user["refresh_token"])), user["id"]))
    db.close()


SEALED = "enc:"
_FERNET = {}


def fernet():
    """TOKEN_ENCRYPTION_KEY tanımlıysa şifreleyici, değilse None."""
    key = CFG["token_key"]
    if not key:
        return None
    if key not in _FERNET:
        try:
            from cryptography.fernet import Fernet
        except ImportError:
            raise SystemExit("TOKEN_ENCRYPTION_KEY tanımlı ama 'cryptography' paketi yok: pip install cryptography")
        _FERNET[key] = Fernet(key.encode())
    return _FERNET[key]


def seal(value):
    """Token'ı veritabanına yazmadan önce şifreler."""
    cipher = fernet()
    if not cipher or not value or value.startswith(SEALED):
        return value
    return SEALED + cipher.encrypt(value.encode()).decode()


def unseal(value):
    """Veritabanındaki token'ı çözer; anahtar yanlışsa boş döner ve kullanıcı yeniden giriş yapar."""
    if not value.startswith(SEALED):
        return value
    cipher = fernet()
    if not cipher:
        return ""
    try:
        return cipher.decrypt(value[len(SEALED):].encode()).decode()
    except Exception:
        return ""


class ApiError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


def text_field(body, key, label, default=""):
    """Gövdedeki metin alanı. null, liste, sayı gibi değerler str() ile "None", "[]" olmasın diye 400 döner."""
    value = body.get(key, default)
    if not isinstance(value, str):
        raise ApiError(400, f"{label} metin olmalı")
    return value.strip()


class Redirect(Exception):
    def __init__(self, url):
        super().__init__(url)
        self.url = url


@contextlib.contextmanager
def transaction(db):
    """Birden çok yazmayı tek adımda uygular; hata olursa hiçbiri kalmaz."""
    db.execute("BEGIN IMMEDIATE")
    try:
        yield
        db.execute("COMMIT")
    except BaseException:
        db.execute("ROLLBACK")
        raise


# ---------------------------------------------------------------- Kick API

class RateLimiter:
    """Kick API isteklerini eşit aralıklarla dağıtır ve hızı Kick'in tepkisine göre ayarlar."""

    def __init__(self, rate, ceiling):
        self.rate, self.ceiling = rate, ceiling   # rate <= 0 ise sınırlama kapalıdır
        self.lock = threading.Lock()
        self.next_slot = 0.0
        self.streak = 0
        self.last_429 = 0.0
        self.known_limit = ceiling   # 429 alınan hızın biraz altı; bir süre bunun üstüne çıkılmaz
        self.limit_until = 0.0

    def acquire(self):
        if self.rate <= 0:
            return
        with self.lock:
            now = time.time()
            slot = max(now, self.next_slot)
            self.next_slot = slot + 1 / self.rate
        if slot > now:
            time.sleep(slot - now)

    def report(self, status):
        if self.rate <= 0:
            return
        with self.lock:
            now = time.time()
            if status == 429:
                self.streak = 0
                self.next_slot = max(self.next_slot, now + 5)
                # Aynı anda gelen 429'lar tek bir uyarı sayılır; yoksa hız bir anda dibe iner.
                if now - self.last_429 > 10:
                    self.known_limit, self.limit_until = self.rate * 0.85, now + 900
                    self.rate = max(0.4, self.rate * 0.7)
                    print(f"Kick istek sınırı: hız {self.rate:.2f} istek/sn'ye düşürüldü")
                self.last_429 = now
            else:
                self.streak += 1
                limit = self.known_limit if now < self.limit_until else self.ceiling
                if self.streak >= 40 and self.rate < limit:
                    self.streak = 0
                    self.rate = min(limit, self.rate * 1.2)
                    print(f"Kick istek hızı {self.rate:.2f} istek/sn'ye çıkarıldı")


LIMITER = RateLimiter(CFG["kick_rps"], CFG["kick_rps_max"])


def http(method, url, token=None, form=None, body=None):
    """(status, json) döndürür; ağ hatasında status 0 olur."""
    limited = url.startswith(CFG["kick_api"])
    if limited:
        LIMITER.acquire()
    headers = {"Accept": "application/json", "User-Agent": "kick-crossban/0.1"}
    data = None
    if form is not None:
        data = urllib.parse.urlencode(form).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    elif body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            status, raw = res.status, res.read()
    except urllib.error.HTTPError as e:
        status, raw = e.code, e.read()
        if status == 429:
            hints = {k: v for k, v in e.headers.items() if "rate" in k.lower() or "retry" in k.lower()}
            if hints:
                print(f"Kick 429 başlıkları: {hints}")
    except OSError as e:   # URLError, zaman aşımı ve yanıt gelmeden kopan bağlantı
        return 0, {"message": str(e)}
    if limited:
        LIMITER.report(status)
    try:
        payload = json.loads(raw) if raw else {}
    except ValueError:
        payload = {"message": raw[:200].decode("utf-8", "replace")}
    return status, payload if isinstance(payload, dict) else {"data": payload}


def store_tokens(db, user_id, name, tokens):
    expires_at = int(time.time()) + int(tokens.get("expires_in", 3600))
    db.execute(
        "INSERT INTO users (id, name, access_token, refresh_token, expires_at) VALUES (?,?,?,?,?) "
        "ON CONFLICT(id) DO UPDATE SET name=excluded.name, access_token=excluded.access_token, "
        "refresh_token=excluded.refresh_token, expires_at=excluded.expires_at",
        (user_id, name, seal(tokens["access_token"]), seal(tokens.get("refresh_token", "")), expires_at),
    )


REFRESH_LOCK = threading.Lock()


def fresh_token(db, user):
    """Kullanıcının geçerli access token'ı; yenilenemiyorsa None."""
    if user["expires_at"] - 60 > time.time():
        return unseal(user["access_token"])
    # Refresh token tek kullanımlık olabilir: aynı anda iki iş parçacığı yenilemesin,
    # bekleyen iş parçacığı diğerinin kaydettiği token'ı kullansın.
    with REFRESH_LOCK:
        user = db.execute("SELECT * FROM users WHERE id = ?", (user["id"],)).fetchone()
        if user["expires_at"] - 60 > time.time():
            return unseal(user["access_token"])
        status, tokens = http("POST", CFG["kick_id"] + "/oauth/token", form={
            "grant_type": "refresh_token",
            "refresh_token": unseal(user["refresh_token"]),
            "client_id": CFG["client_id"],
            "client_secret": CFG["client_secret"],
        })
        if status != 200 or "access_token" not in tokens:
            return None
        tokens.setdefault("refresh_token", unseal(user["refresh_token"]))
        store_tokens(db, user["id"], user["name"], tokens)
        return tokens["access_token"]


def to_slug(value):
    """Kullanıcı adı, @ad, kick.com/ad ya da https://kick.com/ad -> kanal slug'ı."""
    value = value.strip() if isinstance(value, str) else ""
    value = re.sub(r"^(https?://)?(www\.)?kick\.com/", "", value, flags=re.I)
    value = value.split("/")[0].split("?")[0].lstrip("@").lower().replace("_", "-")
    if not re.fullmatch(r"[a-z0-9-]{1,25}", value):
        raise ApiError(400, "Geçersiz kullanıcı adı (Kick adları en fazla 25 karakterdir)")
    return value


def lookup_many(db, actor, slugs):
    """Tek istekte birden çok slug sorgular; {slug: user_id} döner, bulunamayanlar sözlükte olmaz.

    Kick'te her kullanıcının bir kanalı vardır; broadcaster_user_id = user_id.
    """
    token = fresh_token(db, actor)
    if not token:
        raise ApiError(401, "Kick oturumun yenilenemedi, yeniden giriş yap")
    status, payload = http("GET", CFG["kick_api"] + "/public/v1/channels?" +
                           urllib.parse.urlencode([("slug", slug) for slug in slugs]), token=token)
    if status == 429:
        raise ApiError(429, "Kick istek sınırına takıldı, biraz sonra tekrar dene")
    if status == 400:
        raise ApiError(400, "Kick bu kullanıcı adını geçersiz buldu")
    if status != 200:
        raise ApiError(502, f"Kick kullanıcı sorgusu başarısız ({status})")
    return {d["slug"]: int(d["broadcaster_user_id"]) for d in payload.get("data") or [] if d.get("slug")}


def lookup_channel(db, actor, name):
    slug = to_slug(name)
    found = lookup_many(db, actor, [slug])
    if slug not in found:
        raise ApiError(404, f"'{slug}' Kick'te bulunamadı")
    return found[slug], slug


def channel_candidates(db, team_id, actor, channel):
    """Bir kanalda denenecek (token, yetki türü, kullanıcı adı) listesi.

    Önce işlemi yapan moderatör; olmazsa, ekipte olan ve yetkisini ekiple paylaşmayı açmış yayıncı.
    """
    users = [(actor, "broadcaster" if actor["id"] == channel["broadcaster_id"] else "mod")]
    if actor["id"] != channel["broadcaster_id"]:
        owner = db.execute(
            "SELECT u.* FROM users u JOIN members m ON m.user_id = u.id "
            "WHERE u.id = ? AND m.team_id = ? AND m.lend = 1", (channel["broadcaster_id"], team_id)).fetchone()
        if owner:
            users.append((owner, "broadcaster"))
    return [(fresh_token(db, user), via, user["name"]) for user, via in users]


KICK_ERRORS = {
    0: "Kick'e ulaşılamadı",
    401: "Kick oturumu geçersiz; çıkış yapıp yeniden giriş yap",
    403: "bu kanalda ban yetkin yok (moderatör değilsin)",
    404: "kullanıcı ya da kanal Kick'te bulunamadı",
    429: "Kick istek sınırı; biraz sonra tekrar dene",
}


def call_channel(candidates, body, unban):
    """Yalnızca ağ isteği yapar (iş parçacığında çalışır); (başarılı mı, ayrıntı, yetki türü) döner."""
    detail, via = "", candidates[0][1]
    for token, via, name in candidates:
        if not token:
            detail = f"{name}: Kick oturumu yenilenemedi"
            continue
        for attempt in range(2):
            status, payload = http("DELETE" if unban else "POST",
                                   CFG["kick_api"] + "/public/v1/moderation/bans", token=token, body=body)
            if status != 429 or attempt:
                break
            time.sleep(2)
        if 200 <= status < 300:
            return True, "", via
        detail = f"{status}: {KICK_ERRORS.get(status) or payload.get('message') or payload.get('error') or 'hata'}"
    return False, detail, via


def apply_ban(db, ban, actor, unban=False, only_unfinished=False):
    channels = db.execute("SELECT * FROM channels WHERE team_id = ? ORDER BY slug",
                          (ban["team_id"],)).fetchall()
    done = {r["broadcaster_id"]: r["status"] for r in db.execute(
        "SELECT broadcaster_id, status FROM ban_results WHERE ban_id = ?", (ban["id"],))}
    jobs = []
    for channel in channels:
        current = done.get(channel["broadcaster_id"])
        if unban and current not in ("ok", "unban_failed"):
            continue
        if only_unfinished and current == "ok":
            continue
        body = {"broadcaster_user_id": channel["broadcaster_id"], "user_id": ban["target_id"]}
        if not unban:
            if ban["duration"]:
                body["duration"] = ban["duration"]
            if ban["reason"]:
                body["reason"] = ban["reason"]
        jobs.append((channel, channel_candidates(db, ban["team_id"], actor, channel), body))
    if not jobs:
        return
    # Kanallara aynı anda istek atılır; veritabanına yalnızca bu iş parçacığı yazar.
    with ThreadPoolExecutor(max_workers=min(MAX_PARALLEL_CHANNELS, len(jobs))) as pool:
        outcomes = list(pool.map(lambda job: call_channel(job[1], job[2], unban), jobs))
    for (channel, _, _), (ok, detail, via) in zip(jobs, outcomes):
        status = ("unbanned" if ok else "unban_failed") if unban else ("ok" if ok else "failed")
        db.execute(
            "INSERT INTO ban_results (ban_id, broadcaster_id, status, detail, via, updated_at) "
            "VALUES (?,?,?,?,?,?) ON CONFLICT(ban_id, broadcaster_id) DO UPDATE SET "
            "status=excluded.status, detail=excluded.detail, via=excluded.via, "
            "updated_at=excluded.updated_at",
            (ban["id"], channel["broadcaster_id"], status, detail, via, int(time.time())))


def ban_json(db, ban):
    results = {r["broadcaster_id"]: r for r in db.execute(
        "SELECT * FROM ban_results WHERE ban_id = ?", (ban["id"],))}
    channels = db.execute("SELECT * FROM channels WHERE team_id = ? ORDER BY slug",
                          (ban["team_id"],)).fetchall()
    creator = db.execute("SELECT name FROM users WHERE id = ?", (ban["created_by"],)).fetchone()
    return {
        "id": ban["id"],
        "target_id": ban["target_id"],
        "target_name": ban["target_name"],
        "reason": ban["reason"],
        "duration": ban["duration"],
        "created_by": creator["name"] if creator else "?",
        "created_by_id": ban["created_by"],
        "created_at": ban["created_at"],
        "revoked_at": ban["revoked_at"],
        "results": [{
            "slug": c["slug"],
            "status": results[c["broadcaster_id"]]["status"] if c["broadcaster_id"] in results else "pending",
            "detail": results[c["broadcaster_id"]]["detail"] if c["broadcaster_id"] in results else "",
            "via": results[c["broadcaster_id"]]["via"] if c["broadcaster_id"] in results else "",
        } for c in channels],
    }


# ---------------------------------------------------------------- handlers

class Req:
    def __init__(self, db, query, body, user, ip=""):
        self.db, self.query, self.body, self.user, self.ip = db, query, body, user, ip
        self.role = None   # team_for doldurur: kullanıcının o ekipteki rolü


LOGIN_HITS = {}                  # adres -> son giriş denemelerinin zamanları
LOGIN_LOCK = threading.Lock()


def throttle_login(ip):
    """Giriş başlatma oturum gerektirmez; aynı adresten art arda çağrılıp veritabanı şişirilemesin."""
    now = time.time()
    with LOGIN_LOCK:
        if len(LOGIN_HITS) > 10_000:
            LOGIN_HITS.clear()
        hits = [t for t in LOGIN_HITS.get(ip, []) if t > now - LOGIN_WINDOW]
        LOGIN_HITS[ip] = hits
        if len(hits) >= LOGIN_LIMIT:
            raise ApiError(429, "Çok fazla giriş denemesi, birkaç dakika sonra tekrar dene")
        hits.append(now)


REQUEST_HITS = {}                # kullanıcı -> (pencere başlangıcı, istek sayısı)


def throttle_user(user_id):
    """Tek bir hesap sunucuyu istek yağmuruna tutamasın."""
    now = time.time()
    with LOGIN_LOCK:
        if len(REQUEST_HITS) > 50_000:
            REQUEST_HITS.clear()
        start, count = REQUEST_HITS.get(user_id, (now, 0))
        if now - start > REQUEST_WINDOW:
            start, count = now, 0
        REQUEST_HITS[user_id] = (start, count + 1)
    if count >= REQUEST_LIMIT:
        raise ApiError(429, "Çok hızlı istek gönderiyorsun; bir dakika sonra tekrar dene")


KICK_CALLS = {}                  # kullanıcı -> Kick'e giden, sürmekte olan işlem sayısı


@contextlib.contextmanager
def kick_slot(user_id):
    """Bir kullanıcının aynı anda yürüttüğü Kick işlemlerini sınırlar.

    Kick isteklerinin hız sınırı tüm kullanıcılar için ortak; 50 kanallı bir ekipte art arda gelen
    banlar diğer herkesin işlemini bekletebilir.
    """
    with LOGIN_LOCK:
        if KICK_CALLS.get(user_id, 0) >= MAX_KICK_CALLS_PER_USER:
            raise ApiError(429, "Önceki işlemin bitmesini bekle, sonra tekrar dene")
        KICK_CALLS[user_id] = KICK_CALLS.get(user_id, 0) + 1
    try:
        yield
    finally:
        with LOGIN_LOCK:
            KICK_CALLS[user_id] -= 1
            if not KICK_CALLS[user_id]:
                del KICK_CALLS[user_id]


def role_of(team, user_id, role):
    if team["owner_id"] == user_id:
        return "owner"
    return role if role in ASSIGNABLE else "viewer"


def team_for(req, team_id, need="viewer"):
    """Kullanıcının üyesi olduğu ekibi döndürür; rolü `need`in altındaysa 403."""
    team = req.db.execute(
        "SELECT t.*, m.role, m.lend FROM teams t JOIN members m ON m.team_id = t.id "
        "WHERE t.id = ? AND m.user_id = ?", (int(team_id), req.user["id"])).fetchone()
    if not team:
        raise ApiError(404, "Ekip bulunamadı")
    req.role = role_of(team, req.user["id"], team["role"])
    if ROLES[req.role] < ROLES[need]:
        raise ApiError(403, NEED_MESSAGE[need])
    return team


def ban_for(req, team, ban_id):
    ban = req.db.execute("SELECT * FROM bans WHERE id = ? AND team_id = ?",
                         (int(ban_id), team["id"])).fetchone()
    if not ban:
        raise ApiError(404, "Ban kaydı bulunamadı")
    return ban


def auth_login(req):
    redirect = req.query.get("redirect", "")
    match = REDIRECT_RE.fullmatch(redirect)
    if not match or (CFG["extension_ids"] and match.group(1) not in CFG["extension_ids"]):
        raise ApiError(400, "Geçersiz redirect adresi")
    if not CFG["client_id"] or not CFG["client_secret"]:
        raise ApiError(500, "Sunucuda KICK_CLIENT_ID / KICK_CLIENT_SECRET ayarlı değil")
    throttle_login(req.ip)
    state, verifier = secrets.token_urlsafe(24), secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    req.db.execute("DELETE FROM oauth_states WHERE created_at < ?", (int(time.time()) - 600,))
    req.db.execute("INSERT INTO oauth_states VALUES (?,?,?,?)",
                   (state, verifier, redirect, int(time.time())))
    raise Redirect(CFG["kick_id"] + "/oauth/authorize?" + urllib.parse.urlencode({
        "client_id": CFG["client_id"],
        "response_type": "code",
        "redirect_uri": CFG["public_url"] + "/auth/callback",
        "scope": SCOPES,
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }))


def auth_callback(req):
    row = req.db.execute("SELECT * FROM oauth_states WHERE state = ?",
                         (req.query.get("state", ""),)).fetchone()
    if not row or row["created_at"] < time.time() - 600:
        raise ApiError(400, "Giriş isteği geçersiz ya da süresi dolmuş")
    req.db.execute("DELETE FROM oauth_states WHERE state = ?", (row["state"],))

    def fail(message):
        # Bu noktada pencere Kick'ten dönmüştür; ham JSON yerine extension'a dönülür, mesajı panel gösterir.
        return Redirect(row["redirect"].split("#")[0] + "#error=" + urllib.parse.quote(message))

    if "code" not in req.query:
        raise fail("Kick girişi onaylanmadı")
    status, tokens = http("POST", CFG["kick_id"] + "/oauth/token", form={
        "grant_type": "authorization_code",
        "code": req.query["code"],
        "client_id": CFG["client_id"],
        "client_secret": CFG["client_secret"],
        "redirect_uri": CFG["public_url"] + "/auth/callback",
        "code_verifier": row["verifier"],
    })
    if status != 200 or "access_token" not in tokens:
        raise fail("Kick girişi tamamlanamadı; biraz sonra tekrar dene")
    status, me = http("GET", CFG["kick_api"] + "/public/v1/users", token=tokens["access_token"])
    data = me.get("data") or []
    if status != 200 or not data:
        raise fail("Kick hesap bilgisi alınamadı; biraz sonra tekrar dene")
    user_id = int(data[0]["user_id"])
    store_tokens(req.db, user_id, data[0].get("name") or str(user_id), tokens)
    session = secrets.token_urlsafe(32)
    now = int(time.time())
    req.db.execute("DELETE FROM sessions WHERE last_used < ?", (now - SESSION_TTL,))
    req.db.execute("INSERT INTO sessions (token_hash, user_id, created_at, last_used) VALUES (?,?,?,?)",
                   (hashlib.sha256(session.encode()).hexdigest(), user_id, now, now))
    raise Redirect(row["redirect"].split("#")[0] + "#token=" + session)


def auth_logout(req):
    req.db.execute("DELETE FROM sessions WHERE user_id = ?", (req.user["id"],))
    return {}


def health(req):
    return {"ok": True, "version": VERSION}


def me(req):
    teams = req.db.execute(
        "SELECT t.id, t.name, t.owner_id, m.role FROM teams t JOIN members m ON m.team_id = t.id "
        "WHERE m.user_id = ? ORDER BY t.name", (req.user["id"],)).fetchall()
    return {
        "user": {"id": req.user["id"], "name": req.user["name"]},
        # Panel, ekip kuramayacak kullanıcıya "Yeni ekip" alanını hiç göstermez.
        "can_create_team": not CFG["team_creators"] or req.user["id"] in CFG["team_creators"],
        "teams": [{"id": t["id"], "name": t["name"], "owner": t["owner_id"] == req.user["id"],
                   "role": role_of(t, req.user["id"], t["role"])} for t in teams],
    }


def delete_team(db, team_id):
    """Ekibi ve ona bağlı her kaydı siler; Kick'teki banlara dokunmaz. İşlemi (transaction) çağıran açar."""
    db.execute("DELETE FROM ban_results WHERE ban_id IN (SELECT id FROM bans WHERE team_id = ?)", (team_id,))
    for table in ("bans", "queue", "channels", "members"):
        db.execute(f"DELETE FROM {table} WHERE team_id = ?", (team_id,))
    db.execute("DELETE FROM teams WHERE id = ?", (team_id,))


def account_delete(req):
    """Hesabı ve ona bağlı verileri siler, Kick'e verilen yetkiyi geri alır.

    Başkalarının da üyesi olduğu ekipler habersizce yok olmasın diye önce devir ya da silme istenir.
    """
    uid = req.user["id"]
    shared = req.db.execute(
        "SELECT name FROM teams t WHERE owner_id = ? AND "
        "(SELECT COUNT(*) FROM members m WHERE m.team_id = t.id) > 1 ORDER BY name", (uid,)).fetchall()
    if shared:
        names = ", ".join(f'"{t["name"]}"' for t in shared)
        raise ApiError(409, f"Önce şu ekiplerin sahipliğini devret ya da ekipleri sil: {names}")
    # Başarısız olursa kullanıcı erişimi Kick ayarlarından da iptal edebilir; silme bundan etkilenmez.
    for kind in ("access_token", "refresh_token"):
        token = unseal(req.user[kind])
        if token:
            params = {"token": token, "token_hint_type": kind}
            http("POST", CFG["kick_id"] + "/oauth/revoke?" + urllib.parse.urlencode(params), form=params)
    with transaction(req.db):
        for team in req.db.execute("SELECT id FROM teams WHERE owner_id = ?", (uid,)).fetchall():
            delete_team(req.db, team["id"])
        req.db.execute("DELETE FROM members WHERE user_id = ?", (uid,))
        req.db.execute("DELETE FROM queue WHERE created_by = ?", (uid,))
        req.db.execute("DELETE FROM sessions WHERE user_id = ?", (uid,))
        # Başka ekiplerin listesinde bu kullanıcının attığı banlar kalır. Kayıt bozulmasın diye satır
        # silinmez; kimlik numarası dışındaki her şey (ad, tokenlar) boşaltılır.
        if req.db.execute("SELECT 1 FROM bans WHERE created_by = ? OR revoked_by = ? LIMIT 1", (uid, uid)).fetchone():
            req.db.execute("UPDATE users SET name = 'silinmiş kullanıcı', access_token = '', refresh_token = '', "
                           "expires_at = 0 WHERE id = ?", (uid,))
        else:
            req.db.execute("DELETE FROM users WHERE id = ?", (uid,))
    return {}


def team_create(req):
    name = text_field(req.body, "name", "Ekip adı")[:60]
    if not name:
        raise ApiError(400, "Ekip adı gerekli")
    if CFG["team_creators"] and req.user["id"] not in CFG["team_creators"]:
        raise ApiError(403, "Bu sunucuda yeni ekip kurma kapalı. Ekibinden bir davet kodu isteyip katılabilirsin.")
    owned = req.db.execute("SELECT COUNT(*) FROM teams WHERE owner_id = ?", (req.user["id"],)).fetchone()[0]
    if owned >= MAX_TEAMS_OWNED:
        raise ApiError(400, f"En fazla {MAX_TEAMS_OWNED} ekip kurabilirsin; kullanmadığın bir ekibi silip tekrar dene")
    cur = req.db.execute("INSERT INTO teams (name, invite_code, owner_id) VALUES (?,?,?)",
                         (name, secrets.token_urlsafe(9), req.user["id"]))
    # Ekibi kuran, kendi kanalında yayıncı yetkisini ekibiyle paylaşır; isterse kapatır.
    req.db.execute("INSERT INTO members (team_id, user_id, role, lend) VALUES (?,?,'owner',1)",
                   (cur.lastrowid, req.user["id"]))
    # Kuranın kendi kanalı baştan listede olsun; Kick'te kanal kimliği kullanıcı kimliğiyle aynıdır.
    # Kick'e sormadan addan türetilir, slug yalnızca gösterim için. Sahip isterse kaldırabilir.
    try:
        req.db.execute("INSERT INTO channels (team_id, broadcaster_id, slug) VALUES (?,?,?)",
                       (cur.lastrowid, req.user["id"], to_slug(req.user["name"])))
    except ApiError:
        pass
    return {"id": cur.lastrowid}


def invite_rotate(req, team_id):
    """Eski davet kodunu geçersiz kılar; kod yanlış ellere geçtiyse kullanılır."""
    team = team_for(req, team_id, need="admin")
    code = secrets.token_urlsafe(9)
    req.db.execute("UPDATE teams SET invite_code = ? WHERE id = ?", (code, team["id"]))
    return {"invite_code": code}


def team_update(req, team_id):
    """Ekip ayarları: ad ve davet koduyla katılanların başlangıç rolü."""
    team = team_for(req, team_id, need="owner")
    if "name" in req.body:
        name = text_field(req.body, "name", "Ekip adı")[:60]
        if not name:
            raise ApiError(400, "Ekip adı gerekli")
        req.db.execute("UPDATE teams SET name = ? WHERE id = ?", (name, team["id"]))
    if "join_role" in req.body:
        if req.body["join_role"] not in ("viewer", "mod"):
            raise ApiError(400, "Yeni katılanlar moderatör ya da izleyici olarak başlayabilir")
        req.db.execute("UPDATE teams SET join_role = ? WHERE id = ?", (req.body["join_role"], team["id"]))
    return {}


def team_join(req):
    team = req.db.execute("SELECT * FROM teams WHERE invite_code = ?",
                          (text_field(req.body, "invite_code", "Davet kodu"),)).fetchone()
    if not team:
        raise ApiError(404, "Davet kodu geçersiz")
    count = lambda where, arg: req.db.execute(f"SELECT COUNT(*) FROM members WHERE {where}", (arg,)).fetchone()[0]
    if not req.db.execute("SELECT 1 FROM members WHERE team_id = ? AND user_id = ?",
                          (team["id"], req.user["id"])).fetchone():
        if count("user_id = ?", req.user["id"]) >= MAX_TEAMS_JOINED:
            raise ApiError(400, f"En fazla {MAX_TEAMS_JOINED} ekibe üye olabilirsin")
        if count("team_id = ?", team["id"]) >= MAX_MEMBERS_PER_TEAM:
            raise ApiError(400, "Bu ekip dolu; ekip sahibine haber ver")
        # Yayıncı yetkisi paylaşımı kapalı başlar: katılan kişi isterse Ekip sekmesinden kendisi açar.
        req.db.execute("INSERT INTO members (team_id, user_id, role, lend) VALUES (?,?,?,0)",
                       (team["id"], req.user["id"], team["join_role"]))
    return {"id": team["id"], "name": team["name"]}


def team_get(req, team_id):
    team = team_for(req, team_id)
    members = req.db.execute(
        "SELECT u.id, u.name, m.role, m.lend FROM users u JOIN members m ON m.user_id = u.id "
        "WHERE m.team_id = ? ORDER BY u.name", (team["id"],)).fetchall()
    member_ids = {m["id"] for m in members}
    lenders = {m["id"] for m in members if m["lend"]}
    channels = req.db.execute("SELECT * FROM channels WHERE team_id = ? ORDER BY slug",
                              (team["id"],)).fetchall()
    return {
        "id": team["id"],
        "name": team["name"],
        "owner": team["owner_id"] == req.user["id"],
        "role": req.role,
        "lend": bool(team["lend"]),
        "join_role": team["join_role"],
        # Davet kodu ban yetkisi dağıtır; yalnızca onu yönetebilenler görür.
        "invite_code": team["invite_code"] if ROLES[req.role] >= ROLES["admin"] else "",
        "members": [{"id": m["id"], "name": m["name"], "owner": m["id"] == team["owner_id"],
                     "role": role_of(team, m["id"], m["role"])} for m in members],
        # broadcaster_joined: kanalın yayıncısı ekipte ve yetkisini paylaşıyor (ban onun yetkisiyle de tutar).
        "channels": [{"broadcaster_id": c["broadcaster_id"], "slug": c["slug"],
                      "broadcaster_joined": c["broadcaster_id"] in lenders,
                      "broadcaster_member": c["broadcaster_id"] in member_ids} for c in channels],
    }


def member_lend(req, team_id):
    """Üyenin, kendi kanalında yayıncı yetkisini ekibe açıp kapatması. Yalnızca kendisi değiştirebilir."""
    team = team_for(req, team_id)
    lend = req.body.get("lend")
    if not isinstance(lend, bool):
        raise ApiError(400, "Geçersiz istek")
    req.db.execute("UPDATE members SET lend = ? WHERE team_id = ? AND user_id = ?",
                   (int(lend), team["id"], req.user["id"]))
    return {"lend": lend}


def member_role(req, team_id, user_id):
    """Üyenin rolünü değiştirir; rol "owner" ise sahipliği ona devreder (eski sahip yönetici olur)."""
    team = team_for(req, team_id, need="owner")
    user_id, role = int(user_id), req.body.get("role")
    if user_id == team["owner_id"]:
        raise ApiError(400, "Ekip sahibinin rolü değiştirilemez; sahipliği başka bir üyeye devredebilirsin")
    if not req.db.execute("SELECT 1 FROM members WHERE team_id = ? AND user_id = ?",
                          (team["id"], user_id)).fetchone():
        raise ApiError(404, "Üye bulunamadı")
    if role == "owner":
        owned = req.db.execute("SELECT COUNT(*) FROM teams WHERE owner_id = ?", (user_id,)).fetchone()[0]
        if owned >= MAX_TEAMS_OWNED:
            raise ApiError(400, "Bu üye daha fazla ekibin sahibi olamaz")
        with transaction(req.db):
            req.db.execute("UPDATE teams SET owner_id = ? WHERE id = ?", (user_id, team["id"]))
            req.db.execute("UPDATE members SET role = 'owner' WHERE team_id = ? AND user_id = ?",
                           (team["id"], user_id))
            req.db.execute("UPDATE members SET role = 'admin' WHERE team_id = ? AND user_id = ?",
                           (team["id"], req.user["id"]))
    elif role in ASSIGNABLE:
        req.db.execute("UPDATE members SET role = ? WHERE team_id = ? AND user_id = ?",
                       (role, team["id"], user_id))
    else:
        raise ApiError(400, "Geçersiz rol")
    return {}


def team_leave(req, team_id):
    team = team_for(req, team_id)
    if req.role == "owner":
        raise ApiError(400, "Ekip sahibi ayrılamaz; önce sahipliği başka bir üyeye devret ya da ekibi sil")
    req.db.execute("DELETE FROM members WHERE team_id = ? AND user_id = ?", (team["id"], req.user["id"]))
    return {}


def member_remove(req, team_id, user_id):
    team = team_for(req, team_id, need="admin")
    user_id = int(user_id)
    if user_id == team["owner_id"]:
        raise ApiError(400, "Ekip sahibi çıkarılamaz")
    target = req.db.execute("SELECT role FROM members WHERE team_id = ? AND user_id = ?",
                            (team["id"], user_id)).fetchone()
    if not target:
        raise ApiError(404, "Üye bulunamadı")
    # Yönetici başka bir yöneticiyi ya da kendini çıkaramaz; kendisi için "ekipten ayrıl" vardır.
    if ROLES[role_of(team, user_id, target["role"])] >= ROLES[req.role]:
        raise ApiError(403, "Yalnızca kendinden düşük yetkili üyeleri çıkarabilirsin")
    req.db.execute("DELETE FROM members WHERE team_id = ? AND user_id = ?", (team["id"], user_id))
    return {}


def team_delete(req, team_id):
    """Ekibi ve ona bağlı her kaydı siler. Kick'teki banlara dokunmaz."""
    team = team_for(req, team_id, need="owner")
    with transaction(req.db):
        delete_team(req.db, team["id"])
    return {}


def channel_add(req, team_id):
    team = team_for(req, team_id, need="admin")
    if req.db.execute("SELECT COUNT(*) FROM channels WHERE team_id = ?",
                      (team["id"],)).fetchone()[0] >= MAX_CHANNELS_PER_TEAM:
        raise ApiError(400, f"Bir ekibe en fazla {MAX_CHANNELS_PER_TEAM} kanal eklenebilir")
    with kick_slot(req.user["id"]):
        broadcaster_id, slug = lookup_channel(req.db, req.user, req.body.get("slug"))
    req.db.execute("INSERT OR REPLACE INTO channels (team_id, broadcaster_id, slug) VALUES (?,?,?)",
                   (team["id"], broadcaster_id, slug))
    return {"broadcaster_id": broadcaster_id, "slug": slug}


def channel_remove(req, team_id, broadcaster_id):
    team = team_for(req, team_id, need="admin")
    req.db.execute("DELETE FROM channels WHERE team_id = ? AND broadcaster_id = ?",
                   (team["id"], int(broadcaster_id)))
    return {}


def ban_list(req, team_id):
    """En yeni 200 kaydı döndürür; ?q= ad ya da sebepte arar, ?revoked=1 kaldırılanları da katar."""
    team = team_for(req, team_id)
    where, args = "team_id = ?", [team["id"]]
    if req.query.get("revoked") != "1":
        where += " AND revoked_at IS NULL"
    query = req.query.get("q", "").strip().lower()
    if query:
        where += " AND (instr(lower(target_name), ?) > 0 OR instr(lower(reason), ?) > 0)"
        args += [query, query]
    bans = req.db.execute(f"SELECT * FROM bans WHERE {where} ORDER BY id DESC LIMIT 200", args).fetchall()
    return {
        "bans": [ban_json(req.db, b) for b in bans],
        "matched": req.db.execute(f"SELECT COUNT(*) FROM bans WHERE {where}", args).fetchone()[0],
        "active_total": req.db.execute(
            "SELECT COUNT(*) FROM bans WHERE team_id = ? AND revoked_at IS NULL", (team["id"],)).fetchone()[0],
    }


def parse_ban_options(body):
    # Sebep isteğe bağlı: hiç gönderilmemesi ya da null olması boş sebep demektir.
    reason = "" if body.get("reason") is None else text_field(body, "reason", "Ban sebebi")[:100]
    duration = body.get("duration")
    if duration is not None and (type(duration) is not int or not 1 <= duration <= 10080):
        raise ApiError(400, "Süre 1 ile 10080 dakika arasında olmalı")
    return reason, duration


def create_ban(db, team, actor, username, reason, duration, resolved=None):
    """Kullanıcıyı ekibin tüm kanallarında banlar; aktif kaydı varsa eksik kanalları tamamlar.

    resolved: (user_id, slug) önceden sorgulandıysa Kick'e yeniden sorulmaz.
    """
    target_id, slug = resolved or lookup_channel(db, actor, username)
    # Sızan bir davet koduyla izleyici olarak katılan biri kendini bandan korumasın diye
    # yalnızca ban yetkisi olan üyeler ve ekibin kanallarının yayıncıları korunur.
    protected = db.execute(
        "SELECT 1 FROM members m JOIN teams t ON t.id = m.team_id WHERE m.team_id = ? AND m.user_id = ? "
        "AND (m.role IN ('mod', 'admin', 'owner') OR t.owner_id = m.user_id) UNION "
        "SELECT 1 FROM channels WHERE team_id = ? AND broadcaster_id = ?",
        (team["id"], target_id, team["id"], target_id)).fetchone()
    if protected:
        raise ApiError(400, "Ekip üyeleri ve ekipteki yayıncılar banlanamaz")
    if not db.execute("SELECT 1 FROM channels WHERE team_id = ?", (team["id"],)).fetchone():
        raise ApiError(400, "Önce ekibe en az bir kanal ekle")
    ban = db.execute(
        "SELECT * FROM bans WHERE team_id = ? AND target_id = ? AND revoked_at IS NULL",
        (team["id"], target_id)).fetchone()
    if not ban:
        cur = db.execute(
            "INSERT INTO bans (team_id, target_id, target_name, reason, duration, created_by, created_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (team["id"], target_id, slug, reason, duration, actor["id"], int(time.time())))
        ban = db.execute("SELECT * FROM bans WHERE id = ?", (cur.lastrowid,)).fetchone()
    apply_ban(db, ban, actor, only_unfinished=True)
    return ban


def ban_create(req, team_id):
    team = team_for(req, team_id, need="mod")
    reason, duration = parse_ban_options(req.body)
    with kick_slot(req.user["id"]):
        ban = create_ban(req.db, team, req.user, req.body.get("username"), reason, duration)
    return ban_json(req.db, ban)


def ban_retry(req, team_id, ban_id):
    """Başarısız olan ve bandan sonra eklenen kanallara yeniden uygular."""
    team = team_for(req, team_id, need="mod")
    ban = ban_for(req, team, ban_id)
    if ban["revoked_at"]:
        raise ApiError(400, "Bu ban kaldırılmış")
    with kick_slot(req.user["id"]):
        apply_ban(req.db, ban, req.user, only_unfinished=True)
    return ban_json(req.db, ban)


def ban_revoke(req, team_id, ban_id):
    team = team_for(req, team_id, need="mod")
    ban = ban_for(req, team, ban_id)
    if ban["created_by"] != req.user["id"] and ROLES[req.role] < ROLES["admin"]:
        raise ApiError(403, "Yalnızca kendi attığın banı kaldırabilirsin; diğerleri için yönetici gerekir")
    with kick_slot(req.user["id"]):
        apply_ban(req.db, ban, req.user, unban=True)
    req.db.execute("UPDATE bans SET revoked_by = ?, revoked_at = ? WHERE id = ?",
                   (req.user["id"], int(time.time()), ban["id"]))
    return ban_json(req.db, ban_for(req, team, ban_id))


def import_create(req, team_id):
    """Uzun listeleri sıraya alır; banları arka plandaki işçi atar."""
    team = team_for(req, team_id, need="mod")
    reason, duration = parse_ban_options(req.body)
    usernames = req.body.get("usernames")
    if not isinstance(usernames, list) or not usernames:
        raise ApiError(400, "Kullanıcı listesi boş")
    if len(usernames) > MAX_IMPORT:
        raise ApiError(400, f"Tek seferde en fazla {MAX_IMPORT} kullanıcı sıraya alınabilir")
    if not req.db.execute("SELECT 1 FROM channels WHERE team_id = ?", (team["id"],)).fetchone():
        raise ApiError(400, "Önce ekibe en az bir kanal ekle")
    waiting = {r["target_name"].lower() for r in req.db.execute(
        "SELECT target_name FROM queue WHERE team_id = ? AND status IN ('pending', 'working')", (team["id"],))}
    room = MAX_QUEUE_PER_TEAM - len(waiting)
    if room <= 0:
        raise ApiError(400, "Sıra dolu; bekleyen kayıtlar işlenince tekrar dene")
    now, added = int(time.time()), 0
    for name in usernames:
        # Metin olmayan öğe atlanır; str() ile null "None" adlı bir Kick kullanıcısına dönüşüp banlanmasın.
        if not isinstance(name, str):
            continue
        name = name.strip().lstrip("@")[:60]
        if not name or name.lower() in waiting or added == room:
            continue
        waiting.add(name.lower())
        req.db.execute(
            "INSERT INTO queue (team_id, target_name, reason, duration, created_by, created_at) "
            "VALUES (?,?,?,?,?,?)", (team["id"], name, reason, duration, req.user["id"], now))
        added += 1
    return {"added": added, "skipped": len(usernames) - added}


def import_status(req, team_id):
    team = team_for(req, team_id)
    counts = {r["status"]: r["n"] for r in req.db.execute(
        "SELECT status, COUNT(*) AS n FROM queue WHERE team_id = ? GROUP BY status", (team["id"],))}
    working = counts.pop("working", 0)
    if working:
        counts["pending"] = counts.get("pending", 0) + working
    problems = req.db.execute(
        "SELECT target_name, status, detail FROM queue WHERE team_id = ? "
        "AND status NOT IN ('pending', 'working', 'done') ORDER BY id LIMIT 500", (team["id"],)).fetchall()
    return {
        "counts": counts,
        "total": sum(counts.values()),
        "problems": [{"name": p["target_name"], "status": p["status"], "detail": p["detail"]}
                     for p in problems],
    }


def import_clear(req, team_id, which):
    """pending: bekleyenleri iptal eder; finished: biten kayıtları özetten temizler."""
    team = team_for(req, team_id, need="mod")
    # İşlenmekte olan kayıtlara dokunulmaz; onlar birkaç saniyede biter.
    where = "status = 'pending'" if which == "pending" else "status NOT IN ('pending', 'working')"
    cur = req.db.execute(f"DELETE FROM queue WHERE team_id = ? AND {where}", (team["id"],))
    return {"removed": cur.rowcount}


RESOLVED = {}                    # (team_id, slug) -> user_id ya da None (Kick'te yok)
RESOLVE_LOCK = threading.Lock()
PAUSE_UNTIL = 0.0                # Kick istek sınırına takılınca tüm işçiler bu ana kadar bekler
LAST_TEAM = 0                    # sırası en son gelen ekip; bir sonraki kayıt başka ekipten seçilir


def resolve_queued(db, row, actor):
    """Sıradaki kaydın Kick kimliğini bulur; sıradaki sonraki adları da aynı istekte sorgular."""
    slug = to_slug(row["target_name"])
    key = (row["team_id"], slug)
    with RESOLVE_LOCK:
        if key not in RESOLVED:
            slugs = [slug]
            for r in db.execute("SELECT target_name FROM queue WHERE team_id = ? AND status = 'pending' "
                                "ORDER BY id LIMIT ?", (row["team_id"], LOOKUP_BATCH * 2)):
                try:
                    other = to_slug(r["target_name"])
                except ApiError:
                    continue
                if other not in slugs and (row["team_id"], other) not in RESOLVED:
                    slugs.append(other)
                if len(slugs) == LOOKUP_BATCH:
                    break
            try:
                found = lookup_many(db, actor, slugs)
            except ApiError as e:
                if e.status != 400 or len(slugs) == 1:
                    raise
                # Gruptaki tek bir ad Kick'e geçersiz gelirse tüm sorgu düşer; yalnızca bu kaydı sor.
                slugs = [slug]
                found = lookup_many(db, actor, slugs)
            for item in slugs:
                RESOLVED[(row["team_id"], item)] = found.get(item)
        user_id = RESOLVED.pop(key)
    if user_id is None:
        raise ApiError(404, f"'{slug}' Kick'te bulunamadı")
    return user_id, slug


def process_next():
    """Sıradaki bir kaydı işler; işlenecek kayıt yoksa False döner."""
    global PAUSE_UNTIL, LAST_TEAM
    if time.time() < PAUSE_UNTIL:
        return False
    db = connect()
    try:
        # Birden çok işçi aynı kaydı almasın diye kayıt tek adımda "working" yapılır.
        # Ekipler sırayla işlenir; bir ekibin uzun listesi diğerlerini bekletmez.
        row = db.execute(
            "UPDATE queue SET status = 'working' WHERE id = (SELECT id FROM queue "
            "WHERE status = 'pending' AND retry_at <= ? ORDER BY team_id <= ?, team_id, id LIMIT 1) RETURNING *",
            (int(time.time()), LAST_TEAM)).fetchone()
        if not row:
            return False
        LAST_TEAM = row["team_id"]

        def finish(status, detail=""):
            db.execute("UPDATE queue SET status = ?, detail = ? WHERE id = ?", (status, detail, row["id"]))

        def retry_later(message):
            # Kick yavaşlattıysa kaydı sıraya geri koy ve tüm işçileri giderek artan süreyle beklet.
            global PAUSE_UNTIL
            print(f"Sıra: '{row['target_name']}' ertelendi ({row['attempts'] + 1}. deneme): {message}")
            if row["attempts"] >= 12:
                return finish("error", message)
            wait = 20 * (row["attempts"] + 1)
            PAUSE_UNTIL = max(PAUSE_UNTIL, time.time() + 15)
            db.execute("UPDATE queue SET status = 'pending', attempts = attempts + 1, retry_at = ? WHERE id = ?",
                       (int(time.time()) + wait, row["id"]))

        team = db.execute("SELECT * FROM teams WHERE id = ?", (row["team_id"],)).fetchone()
        actor = db.execute(
            "SELECT u.*, m.role FROM users u JOIN members m ON m.user_id = u.id WHERE u.id = ? AND m.team_id = ?",
            (row["created_by"], row["team_id"])).fetchone()
        if not team or not actor or ROLES[role_of(team, actor["id"], actor["role"])] < ROLES["mod"]:
            finish("error", "Listeyi yükleyen kişi artık ekipte değil ya da ban yetkisi yok")
            return True
        try:
            resolved = resolve_queued(db, row, actor)
            ban = create_ban(db, team, actor, row["target_name"], row["reason"], row["duration"], resolved)
        except ApiError as e:
            if e.status == 404:
                finish("notfound")
            elif e.status == 400:
                finish("rejected", e.message)
            elif e.status in (429, 502):
                retry_later(e.message)
            else:
                finish("error", e.message)
            return True
        except Exception as e:
            finish("error", repr(e))
            raise
        failed = [r for r in ban_json(db, ban)["results"] if r["status"] != "ok"]
        if any(r["detail"].startswith("429") for r in failed):
            retry_later("Kick istek sınırı")
        elif failed:
            finish("partial", "; ".join(f"{r['slug']}: {r['detail']}" for r in failed))
        else:
            finish("done")
        return True
    finally:
        db.close()


def queue_worker():
    while True:
        try:
            worked = process_next()
        except Exception as e:  # işçi hiçbir koşulda durmamalı
            print(f"Sıra işçisi hatası: {e!r}")
            worked = False
        if not worked:
            time.sleep(1)


# (metot, yol deseni, handler, oturum gerekli mi)
ROUTES = [
    ("GET", r"/auth/login", auth_login, False),
    ("GET", r"/auth/callback", auth_callback, False),
    ("POST", r"/auth/logout", auth_logout, True),
    ("GET", r"/health", health, False),
    ("GET", r"/me", me, True),
    ("DELETE", r"/me", account_delete, True),
    ("POST", r"/teams", team_create, True),
    ("POST", r"/teams/join", team_join, True),
    ("POST", r"/teams/(\d{1,18})/invite", invite_rotate, True),
    ("POST", r"/teams/(\d{1,18})/settings", team_update, True),
    ("POST", r"/teams/(\d{1,18})/leave", team_leave, True),
    ("POST", r"/teams/(\d{1,18})/lend", member_lend, True),
    ("POST", r"/teams/(\d{1,18})/members/(\d{1,18})/role", member_role, True),
    ("GET", r"/teams/(\d{1,18})", team_get, True),
    ("DELETE", r"/teams/(\d{1,18})", team_delete, True),
    ("DELETE", r"/teams/(\d{1,18})/members/(\d{1,18})", member_remove, True),
    ("POST", r"/teams/(\d{1,18})/channels", channel_add, True),
    ("DELETE", r"/teams/(\d{1,18})/channels/(\d{1,18})", channel_remove, True),
    ("GET", r"/teams/(\d{1,18})/bans", ban_list, True),
    ("POST", r"/teams/(\d{1,18})/bans", ban_create, True),
    ("POST", r"/teams/(\d{1,18})/bans/(\d{1,18})/retry", ban_retry, True),
    ("DELETE", r"/teams/(\d{1,18})/bans/(\d{1,18})", ban_revoke, True),
    ("GET", r"/teams/(\d{1,18})/imports", import_status, True),
    ("POST", r"/teams/(\d{1,18})/imports", import_create, True),
    ("DELETE", r"/teams/(\d{1,18})/imports/(pending|finished)", import_clear, True),
]


class Handler(BaseHTTPRequestHandler):
    server_version = "KickCrossban/0.1"
    # Gövdesini yavaş yollayan ya da hiç yollamayan bağlantı bir iş parçacığını süresiz tutmasın.
    timeout = 30

    def log_message(self, fmt, *args):
        # Sorgu dizgesinde OAuth kodu taşındığı için yalnızca yolu yaz.
        print(f"{self.command} {self.path.split('?')[0]} -> {args[1] if len(args) > 1 else ''}")

    def send_json(self, status, payload=None, location=None):
        raw = b"" if payload is None else json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(status)
        # Kimlik doğrulama çerezle değil Bearer token ile yapıldığı için her origin'e açık.
        # Extension kimlikleri tanımlıysa tarayıcıdan yalnızca o extension'lar API'yi çağırabilir.
        origin = self.headers.get("Origin") or ""
        allowed = {f"chrome-extension://{i}" for i in CFG["extension_ids"]}
        if not allowed:
            self.send_header("Access-Control-Allow-Origin", "*")
        elif origin in allowed:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        if location:
            self.send_header("Location", location)
        if raw:
            self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def client_ip(self):
        # Ters vekilin arkasında gerçek adres X-Forwarded-For'un son değeridir; öncekileri istemci uydurabilir.
        forwarded = self.headers.get("X-Forwarded-For") or ""
        if forwarded and self.client_address[0] in ("127.0.0.1", "::1"):
            return forwarded.split(",")[-1].strip()
        return self.client_address[0]

    def dispatch(self):
        url = urllib.parse.urlsplit(self.path)
        query = dict(urllib.parse.parse_qsl(url.query))
        db = connect()
        try:
            for method, pattern, fn, needs_auth in ROUTES:
                match = re.fullmatch(pattern, url.path)
                if method != self.command or not match:
                    continue
                body = {}
                raw_length = self.headers.get("Content-Length") or "0"
                if not raw_length.isdigit():
                    raise ApiError(400, "Geçersiz istek")
                length = int(raw_length)
                if length > MAX_BODY_BYTES:
                    raise ApiError(413, "İstek çok büyük")
                if length:
                    try:
                        body = json.loads(self.rfile.read(length))
                    except (ValueError, RecursionError):
                        raise ApiError(400, "Geçersiz JSON")
                    if not isinstance(body, dict):
                        raise ApiError(400, "Geçersiz JSON")
                user = None
                if needs_auth:
                    token = (self.headers.get("Authorization") or "").removeprefix("Bearer ").strip()
                    token_hash = hashlib.sha256(token.encode()).hexdigest()
                    user = db.execute(
                        "SELECT u.*, s.last_used FROM users u JOIN sessions s ON s.user_id = u.id "
                        "WHERE s.token_hash = ?", (token_hash,)).fetchone()
                    if not user:
                        raise ApiError(401, "Oturum geçersiz")
                    now = int(time.time())
                    if user["last_used"] < now - SESSION_TTL:
                        db.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))
                        raise ApiError(401, "Oturumun süresi doldu, yeniden giriş yap")
                    if now - user["last_used"] > 3600:
                        db.execute("UPDATE sessions SET last_used = ? WHERE token_hash = ?", (now, token_hash))
                    throttle_user(user["id"])
                return self.send_json(200, fn(Req(db, query, body, user, self.client_ip()), *match.groups()))
            self.send_json(404, {"error": "Bulunamadı"})
        except Redirect as r:
            self.send_json(302, location=r.url)
        except ApiError as e:
            self.send_json(e.status, {"error": e.message})
        except Exception:
            # Ayrıntı yalnızca sunucu günlüğüne; istemci bağlantı kopması yerine sade bir yanıt alır.
            print(f"{self.command} {self.path.split('?')[0]} beklenmeyen hata:\n{traceback.format_exc()}")
            self.send_json(500, {"error": "Sunucuda beklenmeyen bir hata oluştu"})
        finally:
            db.close()

    def do_OPTIONS(self):
        self.send_json(204)

    do_GET = do_POST = do_DELETE = dispatch


def main():
    init_db()
    if not CFG["token_key"]:
        print("UYARI: TOKEN_ENCRYPTION_KEY tanımlı değil, Kick tokenları veritabanında düz metin duruyor.")
    if not CFG["extension_ids"]:
        print("UYARI: ALLOWED_EXTENSION_IDS tanımlı değil, her extension kimliğinden giriş kabul ediliyor.")
    # Sunucu iş sürerken kapandıysa yarım kalan kayıtlar sıraya geri döner.
    db = connect()
    db.execute("UPDATE queue SET status = 'pending' WHERE status = 'working'")
    db.close()
    for _ in range(CFG["queue_workers"]):
        threading.Thread(target=queue_worker, daemon=True).start()
    server = ThreadingHTTPServer((CFG["host"], CFG["port"]), Handler)
    print(f"Dinleniyor: http://{CFG['host']}:{CFG['port']}  (callback: {CFG['public_url']}/auth/callback)")
    server.serve_forever()


if __name__ == "__main__":
    main()
