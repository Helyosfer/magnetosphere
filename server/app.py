"""Kick ortak ban listesi sunucusu. Yalnızca standart kütüphane kullanır.

Çalıştırma: python app.py   (ayarlar için .env.example dosyasına bakın)
"""
import base64
import hashlib
import json
import os
import re
import secrets
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
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
    "extension_ids": [x for x in os.environ.get("ALLOWED_EXTENSION_IDS", "").split(",") if x],
    # Kick rate limit'ine takılmamak için kanallar arası bekleme (saniye).
    "delay": float(os.environ.get("BAN_DELAY_SECONDS", "0.4")),
}

SCOPES = "user:read channel:read moderation:ban"
REDIRECT_RE = re.compile(r"https://([a-p]{32})\.chromiumapp\.org/.*")

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
    created_at INTEGER NOT NULL
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
    owner_id INTEGER NOT NULL REFERENCES users(id)
);
CREATE TABLE IF NOT EXISTS members (
    team_id INTEGER NOT NULL REFERENCES teams(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
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
    db.close()


class ApiError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


class Redirect(Exception):
    def __init__(self, url):
        super().__init__(url)
        self.url = url


# ---------------------------------------------------------------- Kick API

def http(method, url, token=None, form=None, body=None):
    """(status, json) döndürür; ağ hatasında status 0 olur."""
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
    except (urllib.error.URLError, TimeoutError) as e:
        return 0, {"message": str(e)}
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
        (user_id, name, tokens["access_token"], tokens.get("refresh_token", ""), expires_at),
    )


def fresh_token(db, user):
    """Kullanıcının geçerli access token'ı; yenilenemiyorsa None."""
    if user["expires_at"] - 60 > time.time():
        return user["access_token"]
    status, tokens = http("POST", CFG["kick_id"] + "/oauth/token", form={
        "grant_type": "refresh_token",
        "refresh_token": user["refresh_token"],
        "client_id": CFG["client_id"],
        "client_secret": CFG["client_secret"],
    })
    if status != 200 or "access_token" not in tokens:
        return None
    tokens.setdefault("refresh_token", user["refresh_token"])
    store_tokens(db, user["id"], user["name"], tokens)
    return tokens["access_token"]


def to_slug(value):
    """Kullanıcı adı, @ad ya da kick.com/ad -> kanal slug'ı."""
    value = (value or "").strip()
    value = re.sub(r"^https?://(www\.)?kick\.com/", "", value, flags=re.I)
    value = value.split("/")[0].split("?")[0].lstrip("@").lower().replace("_", "-")
    if not re.fullmatch(r"[a-z0-9-]{1,50}", value):
        raise ApiError(400, "Geçersiz kullanıcı adı")
    return value


def lookup_channel(db, actor, name):
    """Kick'te her kullanıcının bir kanalı vardır; broadcaster_user_id = user_id."""
    slug = to_slug(name)
    token = fresh_token(db, actor)
    if not token:
        raise ApiError(401, "Kick oturumun yenilenemedi, yeniden giriş yap")
    status, payload = http("GET", CFG["kick_api"] + "/public/v1/channels?" +
                           urllib.parse.urlencode({"slug": slug}), token=token)
    data = payload.get("data") or []
    if status != 200 or not data:
        raise ApiError(404, f"'{slug}' Kick'te bulunamadı")
    return int(data[0]["broadcaster_user_id"]), data[0].get("slug") or slug


def execute_on_channel(db, team_id, actor, channel, ban, unban):
    """Önce işlemi yapan moderatörün, olmazsa ekipteki yayıncının token'ıyla dener."""
    candidates = [(actor, "broadcaster" if actor["id"] == channel["broadcaster_id"] else "mod")]
    if actor["id"] != channel["broadcaster_id"]:
        owner = db.execute(
            "SELECT u.* FROM users u JOIN members m ON m.user_id = u.id "
            "WHERE u.id = ? AND m.team_id = ?", (channel["broadcaster_id"], team_id)).fetchone()
        if owner:
            candidates.append((owner, "broadcaster"))

    body = {"broadcaster_user_id": channel["broadcaster_id"], "user_id": ban["target_id"]}
    if not unban:
        if ban["duration"]:
            body["duration"] = ban["duration"]
        if ban["reason"]:
            body["reason"] = ban["reason"]

    detail, via = "", candidates[0][1]
    for user, via in candidates:
        token = fresh_token(db, user)
        if not token:
            detail = f"{user['name']}: Kick oturumu yenilenemedi"
            continue
        for attempt in range(2):
            status, payload = http("DELETE" if unban else "POST",
                                   CFG["kick_api"] + "/public/v1/moderation/bans",
                                   token=token, body=body)
            if status != 429 or attempt:
                break
            time.sleep(2)
        if 200 <= status < 300:
            return True, "", via
        detail = f"{status}: {payload.get('message') or payload.get('error') or 'hata'}"
    return False, detail, via


def apply_ban(db, ban, actor, unban=False, only_unfinished=False):
    channels = db.execute("SELECT * FROM channels WHERE team_id = ? ORDER BY slug",
                          (ban["team_id"],)).fetchall()
    done = {r["broadcaster_id"]: r["status"] for r in db.execute(
        "SELECT broadcaster_id, status FROM ban_results WHERE ban_id = ?", (ban["id"],))}
    first = True
    for channel in channels:
        current = done.get(channel["broadcaster_id"])
        if unban and current not in ("ok", "unban_failed"):
            continue
        if only_unfinished and current == "ok":
            continue
        if not first:
            time.sleep(CFG["delay"])
        first = False
        ok, detail, via = execute_on_channel(db, ban["team_id"], actor, channel, ban, unban)
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
    def __init__(self, db, query, body, user):
        self.db, self.query, self.body, self.user = db, query, body, user


def team_for(req, team_id, owner=False):
    team = req.db.execute(
        "SELECT t.* FROM teams t JOIN members m ON m.team_id = t.id "
        "WHERE t.id = ? AND m.user_id = ?", (int(team_id), req.user["id"])).fetchone()
    if not team:
        raise ApiError(404, "Ekip bulunamadı")
    if owner and team["owner_id"] != req.user["id"]:
        raise ApiError(403, "Bunu yalnızca ekip sahibi yapabilir")
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
    if "code" not in req.query:
        raise ApiError(400, "Kick girişi iptal edildi")
    status, tokens = http("POST", CFG["kick_id"] + "/oauth/token", form={
        "grant_type": "authorization_code",
        "code": req.query["code"],
        "client_id": CFG["client_id"],
        "client_secret": CFG["client_secret"],
        "redirect_uri": CFG["public_url"] + "/auth/callback",
        "code_verifier": row["verifier"],
    })
    if status != 200 or "access_token" not in tokens:
        raise ApiError(502, "Kick token vermedi")
    status, me = http("GET", CFG["kick_api"] + "/public/v1/users", token=tokens["access_token"])
    data = me.get("data") or []
    if status != 200 or not data:
        raise ApiError(502, "Kick kullanıcı bilgisi alınamadı")
    user_id = int(data[0]["user_id"])
    store_tokens(req.db, user_id, data[0].get("name") or str(user_id), tokens)
    session = secrets.token_urlsafe(32)
    req.db.execute("INSERT INTO sessions VALUES (?,?,?)",
                   (hashlib.sha256(session.encode()).hexdigest(), user_id, int(time.time())))
    raise Redirect(row["redirect"].split("#")[0] + "#token=" + session)


def auth_logout(req):
    req.db.execute("DELETE FROM sessions WHERE user_id = ?", (req.user["id"],))
    return {}


def me(req):
    teams = req.db.execute(
        "SELECT t.id, t.name, t.owner_id FROM teams t JOIN members m ON m.team_id = t.id "
        "WHERE m.user_id = ? ORDER BY t.name", (req.user["id"],)).fetchall()
    return {
        "user": {"id": req.user["id"], "name": req.user["name"]},
        "teams": [{"id": t["id"], "name": t["name"], "owner": t["owner_id"] == req.user["id"]}
                  for t in teams],
    }


def team_create(req):
    name = str(req.body.get("name", "")).strip()[:60]
    if not name:
        raise ApiError(400, "Ekip adı gerekli")
    cur = req.db.execute("INSERT INTO teams (name, invite_code, owner_id) VALUES (?,?,?)",
                         (name, secrets.token_urlsafe(9), req.user["id"]))
    req.db.execute("INSERT INTO members VALUES (?,?)", (cur.lastrowid, req.user["id"]))
    return {"id": cur.lastrowid}


def team_join(req):
    team = req.db.execute("SELECT * FROM teams WHERE invite_code = ?",
                          (str(req.body.get("invite_code", "")).strip(),)).fetchone()
    if not team:
        raise ApiError(404, "Davet kodu geçersiz")
    req.db.execute("INSERT OR IGNORE INTO members VALUES (?,?)", (team["id"], req.user["id"]))
    return {"id": team["id"]}


def team_get(req, team_id):
    team = team_for(req, team_id)
    members = req.db.execute(
        "SELECT u.id, u.name FROM users u JOIN members m ON m.user_id = u.id "
        "WHERE m.team_id = ? ORDER BY u.name", (team["id"],)).fetchall()
    member_ids = {m["id"] for m in members}
    channels = req.db.execute("SELECT * FROM channels WHERE team_id = ? ORDER BY slug",
                              (team["id"],)).fetchall()
    return {
        "id": team["id"],
        "name": team["name"],
        "owner": team["owner_id"] == req.user["id"],
        "invite_code": team["invite_code"],
        "members": [{"id": m["id"], "name": m["name"], "owner": m["id"] == team["owner_id"]}
                    for m in members],
        "channels": [{"broadcaster_id": c["broadcaster_id"], "slug": c["slug"],
                      "broadcaster_joined": c["broadcaster_id"] in member_ids} for c in channels],
    }


def member_remove(req, team_id, user_id):
    team = team_for(req, team_id, owner=True)
    if int(user_id) == team["owner_id"]:
        raise ApiError(400, "Ekip sahibi çıkarılamaz")
    req.db.execute("DELETE FROM members WHERE team_id = ? AND user_id = ?",
                   (team["id"], int(user_id)))
    return {}


def channel_add(req, team_id):
    team = team_for(req, team_id, owner=True)
    broadcaster_id, slug = lookup_channel(req.db, req.user, req.body.get("slug"))
    req.db.execute("INSERT OR REPLACE INTO channels VALUES (?,?,?)",
                   (team["id"], broadcaster_id, slug))
    return {"broadcaster_id": broadcaster_id, "slug": slug}


def channel_remove(req, team_id, broadcaster_id):
    team = team_for(req, team_id, owner=True)
    req.db.execute("DELETE FROM channels WHERE team_id = ? AND broadcaster_id = ?",
                   (team["id"], int(broadcaster_id)))
    return {}


def ban_list(req, team_id):
    team = team_for(req, team_id)
    bans = req.db.execute("SELECT * FROM bans WHERE team_id = ? ORDER BY id DESC LIMIT 200",
                          (team["id"],)).fetchall()
    return {"bans": [ban_json(req.db, b) for b in bans]}


def ban_create(req, team_id):
    team = team_for(req, team_id)
    reason = str(req.body.get("reason") or "").strip()[:100]
    duration = req.body.get("duration")
    if duration is not None and (not isinstance(duration, int) or not 1 <= duration <= 10080):
        raise ApiError(400, "Süre 1 ile 10080 dakika arasında olmalı")
    target_id, slug = lookup_channel(req.db, req.user, req.body.get("username"))
    protected = req.db.execute(
        "SELECT 1 FROM members WHERE team_id = ? AND user_id = ? UNION "
        "SELECT 1 FROM channels WHERE team_id = ? AND broadcaster_id = ?",
        (team["id"], target_id, team["id"], target_id)).fetchone()
    if protected:
        raise ApiError(400, "Ekip üyeleri ve ekipteki yayıncılar banlanamaz")
    if not req.db.execute("SELECT 1 FROM channels WHERE team_id = ?", (team["id"],)).fetchone():
        raise ApiError(400, "Önce ekibe en az bir kanal ekle")
    ban = req.db.execute(
        "SELECT * FROM bans WHERE team_id = ? AND target_id = ? AND revoked_at IS NULL",
        (team["id"], target_id)).fetchone()
    if not ban:
        cur = req.db.execute(
            "INSERT INTO bans (team_id, target_id, target_name, reason, duration, created_by, created_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (team["id"], target_id, slug, reason, duration, req.user["id"], int(time.time())))
        ban = req.db.execute("SELECT * FROM bans WHERE id = ?", (cur.lastrowid,)).fetchone()
    apply_ban(req.db, ban, req.user, only_unfinished=True)
    return ban_json(req.db, ban)


def ban_retry(req, team_id, ban_id):
    """Başarısız olan ve bandan sonra eklenen kanallara yeniden uygular."""
    team = team_for(req, team_id)
    ban = ban_for(req, team, ban_id)
    if ban["revoked_at"]:
        raise ApiError(400, "Bu ban kaldırılmış")
    apply_ban(req.db, ban, req.user, only_unfinished=True)
    return ban_json(req.db, ban)


def ban_revoke(req, team_id, ban_id):
    team = team_for(req, team_id)
    ban = ban_for(req, team, ban_id)
    apply_ban(req.db, ban, req.user, unban=True)
    req.db.execute("UPDATE bans SET revoked_by = ?, revoked_at = ? WHERE id = ?",
                   (req.user["id"], int(time.time()), ban["id"]))
    return ban_json(req.db, ban_for(req, team, ban_id))


# (metot, yol deseni, handler, oturum gerekli mi)
ROUTES = [
    ("GET", r"/auth/login", auth_login, False),
    ("GET", r"/auth/callback", auth_callback, False),
    ("POST", r"/auth/logout", auth_logout, True),
    ("GET", r"/me", me, True),
    ("POST", r"/teams", team_create, True),
    ("POST", r"/teams/join", team_join, True),
    ("GET", r"/teams/(\d+)", team_get, True),
    ("DELETE", r"/teams/(\d+)/members/(\d+)", member_remove, True),
    ("POST", r"/teams/(\d+)/channels", channel_add, True),
    ("DELETE", r"/teams/(\d+)/channels/(\d+)", channel_remove, True),
    ("GET", r"/teams/(\d+)/bans", ban_list, True),
    ("POST", r"/teams/(\d+)/bans", ban_create, True),
    ("POST", r"/teams/(\d+)/bans/(\d+)/retry", ban_retry, True),
    ("DELETE", r"/teams/(\d+)/bans/(\d+)", ban_revoke, True),
]


class Handler(BaseHTTPRequestHandler):
    server_version = "KickCrossban/0.1"

    def log_message(self, fmt, *args):
        # Sorgu dizgesinde OAuth kodu taşındığı için yalnızca yolu yaz.
        print(f"{self.command} {self.path.split('?')[0]} -> {args[1] if len(args) > 1 else ''}")

    def send_json(self, status, payload=None, location=None):
        raw = b"" if payload is None else json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(status)
        # Kimlik doğrulama çerezle değil Bearer token ile yapıldığı için her origin'e açık.
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        if location:
            self.send_header("Location", location)
        if raw:
            self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

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
                length = int(self.headers.get("Content-Length") or 0)
                if length:
                    try:
                        body = json.loads(self.rfile.read(length))
                    except ValueError:
                        raise ApiError(400, "Geçersiz JSON")
                    if not isinstance(body, dict):
                        raise ApiError(400, "Geçersiz JSON")
                user = None
                if needs_auth:
                    token = (self.headers.get("Authorization") or "").removeprefix("Bearer ").strip()
                    user = db.execute(
                        "SELECT u.* FROM users u JOIN sessions s ON s.user_id = u.id "
                        "WHERE s.token_hash = ?",
                        (hashlib.sha256(token.encode()).hexdigest(),)).fetchone()
                    if not user:
                        raise ApiError(401, "Oturum geçersiz")
                return self.send_json(200, fn(Req(db, query, body, user), *match.groups()))
            self.send_json(404, {"error": "Bulunamadı"})
        except Redirect as r:
            self.send_json(302, location=r.url)
        except ApiError as e:
            self.send_json(e.status, {"error": e.message})
        finally:
            db.close()

    def do_OPTIONS(self):
        self.send_json(204)

    do_GET = do_POST = do_DELETE = dispatch


def main():
    init_db()
    server = ThreadingHTTPServer((CFG["host"], CFG["port"]), Handler)
    print(f"Dinleniyor: http://{CFG['host']}:{CFG['port']}  (callback: {CFG['public_url']}/auth/callback)")
    server.serve_forever()


if __name__ == "__main__":
    main()
