"""Sahte bir Kick API'sine karşı uçtan uca testler: python -m unittest test_app"""
import http.client
import json
import os
import sqlite3
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from cryptography.fernet import Fernet

import app

REDIRECT = "https://" + "a" * 32 + ".chromiumapp.org/"

# Sahte Kick: kullanıcı kimliği N için token "tok-N", kanal slug'ı USERS[N].
USERS = {1: "yayinci-a", 2: "yayinci-b", 3: "yayinci-c", 10: "mod-ali", 11: "mod-veli",
         20: "sahip-s", 21: "yonetici-y", 22: "mod-m", 23: "izleyici-i", 24: "yeni-n", 99: "trol"}
# mod-ali yalnızca yayinci-a'da, mod-m yalnızca yayinci-c'de moderatör
MODS = {1: {10}, 2: set(), 3: {22}, 20: set()}
BANNED = set()               # (broadcaster_id, user_id)
LOOKUPS = []                 # her kullanıcı sorgusunda istenen slug listesi
REVOKED = set()              # hesap silinince geri alınan tokenlar


class FakeKick(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, status, payload):
        raw = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def uid(self):
        return int(self.headers["Authorization"].removeprefix("Bearer tok-"))

    def body(self):
        return self.rfile.read(int(self.headers.get("Content-Length") or 0))

    def do_GET(self):
        url = urllib.parse.urlsplit(self.path)
        if url.path == "/public/v1/users":
            return self.reply(200, {"data": [{"user_id": self.uid(), "name": USERS[self.uid()]}]})
        if url.path == "/public/v1/channels":
            slugs = urllib.parse.parse_qs(url.query)["slug"]
            LOOKUPS.append(slugs)
            if any(len(s) > 25 for s in slugs):
                return self.reply(400, {"message": "Invalid request"})
            data = [{"broadcaster_user_id": i, "slug": s} for i, s in USERS.items() if s in slugs]
            return self.reply(200, {"data": data})
        self.reply(404, {})

    def do_POST(self):
        if self.path == "/oauth/token":
            form = dict(urllib.parse.parse_qsl(self.body().decode()))
            return self.reply(200, {"access_token": "tok-" + form["code"],
                                    "refresh_token": "ref", "expires_in": 3600})
        if self.path.startswith("/oauth/revoke"):
            REVOKED.add(dict(urllib.parse.parse_qsl(self.body().decode()))["token"])
            return self.reply(200, {})
        self.moderate(banned=True)

    def do_DELETE(self):
        self.moderate(banned=False)

    def moderate(self, banned):
        body = json.loads(self.body())
        channel = body["broadcaster_user_id"]
        if self.uid() != channel and self.uid() not in MODS[channel]:
            return self.reply(403, {"message": "Forbidden"})
        key = (channel, body["user_id"])
        BANNED.add(key) if banned else BANNED.discard(key)
        self.reply(200, {"data": {}})


def serve(handler):
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


OPENER = urllib.request.build_opener(NoRedirect)


def call(base, method, path, token=None, body=None, origin=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    if origin:
        headers["Origin"] = origin
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(base + path, data=data, method=method, headers=headers)
    try:
        with OPENER.open(req) as res:
            return res.status, json.loads(res.read() or b"{}"), res.headers
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}"), e.headers


class CrossBanTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.kick, kick_url = serve(FakeKick)
        cls.tmp = tempfile.TemporaryDirectory()
        app.CFG.update(client_id="id", client_secret="secret", kick_id=kick_url, kick_api=kick_url,
                       db=os.path.join(cls.tmp.name, "test.db"),
                       token_key=Fernet.generate_key().decode(),
                       extension_ids=[])   # yerel .env'deki kimlik kısıtı testi etkilemesin
        app.LIMITER.rate = 0   # sahte Kick'e karşı hız sınırı gereksiz
        app.REQUEST_LIMIT = 10 ** 6   # istek sınırı yalnızca kendi testinde denenir
        app.init_db()
        cls.server, cls.base = serve(app.Handler)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.kick.shutdown()
        cls.server.server_close()
        cls.kick.server_close()
        cls.tmp.cleanup()

    def login(self, uid):
        status, _, headers = call(self.base, "GET", "/auth/login?redirect=" + urllib.parse.quote(REDIRECT))
        self.assertEqual(status, 302)
        state = urllib.parse.parse_qs(urllib.parse.urlsplit(headers["Location"]).query)["state"][0]
        status, _, headers = call(self.base, "GET", f"/auth/callback?code={uid}&state={state}")
        self.assertEqual(status, 302)
        self.assertTrue(headers["Location"].startswith(REDIRECT + "#token="))
        return headers["Location"].split("#token=")[1]

    def test_flow(self):
        ali = self.login(10)
        veli = self.login(11)

        # Yabancı bir adrese yönlendirme reddedilir.
        self.assertEqual(call(self.base, "GET", "/auth/login?redirect=https://evil.example/")[0], 400)
        self.assertEqual(call(self.base, "GET", "/me", "yanlis")[0], 401)

        _, team, _ = call(self.base, "POST", "/teams", ali, {"name": "Ekip"})
        tid = team["id"]
        _, info, _ = call(self.base, "GET", f"/teams/{tid}", ali)
        # Kuranın kendi kanalı ekip kurulunca listeye kendiliğinden girer.
        self.assertEqual([(c["broadcaster_id"], c["slug"]) for c in info["channels"]], [(10, "mod-ali")])
        # Sahip istemezse kaldırabilir; akışın geri kalanı yalnızca elle eklenen kanallarla sürer.
        self.assertEqual(call(self.base, "DELETE", f"/teams/{tid}/channels/10", ali)[0], 200)

        # Üye olmayan ekibi göremez; davet koduyla katılır ama kanal ekleyemez.
        self.assertEqual(call(self.base, "GET", f"/teams/{tid}", veli)[0], 404)
        self.assertEqual(call(self.base, "POST", "/teams/join", veli, {"invite_code": info["invite_code"]})[0], 200)
        self.assertEqual(call(self.base, "POST", f"/teams/{tid}/channels", veli, {"slug": "yayinci-a"})[0], 403)

        for slug in ("yayinci-a", "Yayinci_B"):
            self.assertEqual(call(self.base, "POST", f"/teams/{tid}/channels", ali, {"slug": slug})[0], 200)

        # Ekip üyesi ve ekipteki yayıncı banlanamaz.
        self.assertEqual(call(self.base, "POST", f"/teams/{tid}/bans", ali, {"username": "mod-veli"})[0], 400)
        self.assertEqual(call(self.base, "POST", f"/teams/{tid}/bans", ali, {"username": "yayinci-b"})[0], 400)
        self.assertEqual(call(self.base, "POST", f"/teams/{tid}/bans", ali, {"username": "yok-boyle-biri"})[0], 404)

        # mod-ali yalnızca yayinci-a'da moderatör: orada tutar, yayinci-b'de reddedilir.
        status, ban, _ = call(self.base, "POST", f"/teams/{tid}/bans", ali,
                              {"username": "@trol", "reason": "spam"})
        self.assertEqual(status, 200)
        by_slug = {r["slug"]: r for r in ban["results"]}
        self.assertEqual(by_slug["yayinci-a"]["status"], "ok")
        self.assertEqual(by_slug["yayinci-a"]["via"], "mod")
        self.assertEqual(by_slug["yayinci-b"]["status"], "failed")
        self.assertEqual(BANNED, {(1, 99)})

        # yayinci-b ekibe katılır; yetkisini paylaşmayı kendisi açmadıkça token'ı kullanılmaz.
        yayinci_b = self.login(2)
        call(self.base, "POST", "/teams/join", yayinci_b, {"invite_code": info["invite_code"]})
        _, ban, _ = call(self.base, "POST", f"/teams/{tid}/bans/{ban['id']}/retry", ali)
        self.assertEqual({r["slug"]: r["status"] for r in ban["results"]}["yayinci-b"], "failed")
        self.assertIn("moderatör değilsin", {r["slug"]: r["detail"] for r in ban["results"]}["yayinci-b"])
        channels = {c["slug"]: c for c in call(self.base, "GET", f"/teams/{tid}", ali)[1]["channels"]}
        self.assertEqual((channels["yayinci-b"]["broadcaster_member"], channels["yayinci-b"]["broadcaster_joined"]),
                         (True, False))
        # Yetkiyi başkası adına açmak mümkün değildir: uç yalnızca çağıranın kendi üyeliğini değiştirir.
        self.assertEqual(call(self.base, "POST", f"/teams/{tid}/lend", yayinci_b, {"lend": True})[0], 200)
        # Paylaşım açılınca tekrar deneme onun token'ına düşer.
        _, ban, _ = call(self.base, "POST", f"/teams/{tid}/bans/{ban['id']}/retry", ali)
        by_slug = {r["slug"]: r for r in ban["results"]}
        self.assertEqual(by_slug["yayinci-b"]["status"], "ok")
        self.assertEqual(by_slug["yayinci-b"]["via"], "broadcaster")
        self.assertEqual(BANNED, {(1, 99), (2, 99)})

        # Aynı kişiyi yeniden banlamak ikinci bir kayıt açmaz.
        call(self.base, "POST", f"/teams/{tid}/bans", veli, {"username": "trol"})
        _, listing, _ = call(self.base, "GET", f"/teams/{tid}/bans", veli)
        self.assertEqual(len(listing["bans"]), 1)
        self.assertEqual((listing["matched"], listing["active_total"]), (1, 1))
        self.assertEqual(call(self.base, "GET", f"/teams/{tid}/bans?q=SPA", veli)[1]["matched"], 1)
        self.assertEqual(call(self.base, "GET", f"/teams/{tid}/bans?q=yok", veli)[1]["matched"], 0)

        # Moderatör başkasının attığı banı kaldıramaz; sahip ve yöneticiler kaldırır.
        self.assertEqual(call(self.base, "DELETE", f"/teams/{tid}/bans/{ban['id']}", veli)[0], 403)
        # Ban kaldırma her kanalda geri alır.
        _, ban, _ = call(self.base, "DELETE", f"/teams/{tid}/bans/{ban['id']}", ali)
        self.assertIsNotNone(ban["revoked_at"])
        self.assertEqual({r["status"] for r in ban["results"]}, {"unbanned"})
        self.assertEqual(BANNED, set())
        # Kaldırılan kayıt varsayılan listede görünmez.
        self.assertEqual(call(self.base, "GET", f"/teams/{tid}/bans", ali)[1]["bans"], [])
        self.assertEqual(call(self.base, "GET", f"/teams/{tid}/bans?revoked=1", ali)[1]["matched"], 1)

        # Sıra: uzun listeler arka planda işlenir; bulunamayan ad diğerlerini durdurmaz.
        status, res, _ = call(self.base, "POST", f"/teams/{tid}/imports", ali,
                              {"usernames": ["trol", "@Trol", "yok-boyle-biri", "mod-veli", "x" * 32],
                               "reason": "liste"})
        self.assertEqual((status, res["added"], res["skipped"]), (200, 4, 1))
        _, st, _ = call(self.base, "GET", f"/teams/{tid}/imports", ali)
        self.assertEqual(st["counts"], {"pending": 4})
        LOOKUPS.clear()
        # Üç işçi aynı anda çalışır; hiçbir kayıt iki kez işlenmez ya da atlanmaz.
        workers = [threading.Thread(target=lambda: [None for _ in iter(app.process_next, False)])
                   for _ in range(3)]
        for w in workers:
            w.start()
        for w in workers:
            w.join()
        # Sıradaki adlar Kick'e tek tek değil, tek istekte sorulur.
        self.assertEqual(len(LOOKUPS), 1)
        self.assertEqual(sorted(LOOKUPS[0]), ["mod-veli", "trol", "yok-boyle-biri"])
        _, st, _ = call(self.base, "GET", f"/teams/{tid}/imports", ali)
        # Fazla uzun ad yalnızca kendisi reddedilir; aynı gruptaki diğerlerini düşürmez.
        self.assertEqual(st["counts"], {"done": 1, "notfound": 1, "rejected": 2})
        self.assertEqual({p["name"]: p["status"] for p in st["problems"]},
                         {"yok-boyle-biri": "notfound", "mod-veli": "rejected", "x" * 32: "rejected"})
        self.assertEqual(BANNED, {(1, 99), (2, 99)})
        self.assertEqual(call(self.base, "DELETE", f"/teams/{tid}/imports/finished", ali)[1]["removed"], 4)
        self.assertEqual(call(self.base, "POST", f"/teams/{tid}/imports", ali, {"usernames": []})[0], 400)

        # Sıraya alan kişinin ban yetkisi sonradan alınırsa bekleyen kayıtları işlenmez.
        call(self.base, "POST", f"/teams/{tid}/imports", veli, {"usernames": ["trol"]})
        self.assertEqual(call(self.base, "POST", f"/teams/{tid}/members/11/role", ali, {"role": "viewer"})[0], 200)
        banned_now = set(BANNED)
        while app.process_next():
            pass
        self.assertEqual(BANNED, banned_now)
        self.assertEqual(call(self.base, "GET", f"/teams/{tid}/imports", ali)[1]["counts"], {"error": 1})
        call(self.base, "DELETE", f"/teams/{tid}/imports/finished", ali)
        call(self.base, "POST", f"/teams/{tid}/members/11/role", ali, {"role": "mod"})
        self.assertEqual(call(self.base, "GET", f"/teams/{tid}/imports", "yanlis")[0], 401)

        # Güvenlik: tokenlar veritabanında şifreli durur.
        db = sqlite3.connect(app.CFG["db"])
        for access, refresh in db.execute("SELECT access_token, refresh_token FROM users"):
            self.assertTrue(access.startswith("enc:") and refresh.startswith("enc:"))
            self.assertNotIn("tok-", access)

        # Davet kodu yenilenince eskisi geçersiz olur; bunu yalnızca sahip yapabilir.
        self.assertEqual(call(self.base, "POST", f"/teams/{tid}/invite", veli)[0], 403)
        _, fresh, _ = call(self.base, "POST", f"/teams/{tid}/invite", ali)
        self.assertNotEqual(fresh["invite_code"], info["invite_code"])
        stranger = self.login(99)
        self.assertEqual(call(self.base, "POST", "/teams/join", stranger, {"invite_code": info["invite_code"]})[0], 404)

        # Çok büyük istek gövdesi okunmadan reddedilir.
        # Sunucu gövdeyi okumadan yanıtlayıp bağlantıyı kapattığı için istemci 413'ü göremeden gönderim
        # sırasında kopabilir (BrokenPipe/ConnectionReset); bu da geçerli bir rettir.
        teams_before = len(call(self.base, "GET", "/me", ali)[1]["teams"])
        try:
            status = call(self.base, "POST", "/teams", ali, {"name": "x" * 1_100_000})[0]
        except (ConnectionError, urllib.error.URLError) as e:
            self.assertIsInstance(getattr(e, "reason", e), ConnectionError)
            status = 413
        self.assertEqual(status, 413)
        self.assertEqual(len(call(self.base, "GET", "/me", ali)[1]["teams"]), teams_before)

        # Extension kimliği sabitlenince yalnızca o extension'a CORS izni verilir ve yalnızca o giriş yapabilir.
        ours, other = "chrome-extension://" + "a" * 32, "chrome-extension://" + "b" * 32
        self.assertEqual(call(self.base, "GET", "/me", ali, origin=other)[2]["Access-Control-Allow-Origin"], "*")
        app.CFG["extension_ids"] = ["a" * 32]
        self.assertEqual(call(self.base, "GET", "/me", ali, origin=ours)[2]["Access-Control-Allow-Origin"], ours)
        self.assertIsNone(call(self.base, "GET", "/me", ali, origin=other)[2]["Access-Control-Allow-Origin"])
        bad = "https://" + "b" * 32 + ".chromiumapp.org/"
        self.assertEqual(call(self.base, "GET", "/auth/login?redirect=" + urllib.parse.quote(bad))[0], 400)
        app.CFG["extension_ids"] = []

        # Uzun süre kullanılmayan oturum geçersiz olur.
        db.execute("UPDATE sessions SET last_used = last_used - ?", (app.SESSION_TTL + 60,))
        db.commit()
        db.close()
        status, res, _ = call(self.base, "GET", "/me", stranger)
        self.assertEqual((status, "süresi doldu" in res["error"]), (401, True))
        ali, veli = self.login(10), self.login(11)

        # Çıkarılan üye ekibe erişemez.
        self.assertEqual(call(self.base, "DELETE", f"/teams/{tid}/members/11", ali)[0], 200)
        self.assertEqual(call(self.base, "GET", f"/teams/{tid}/bans", veli)[0], 404)

        # Ekibi yalnızca sahibi siler; liste, sıra ve üyelikler de gider, Kick'teki banlar kalır.
        banned_before = set(BANNED)
        self.assertEqual(call(self.base, "DELETE", f"/teams/{tid}", self.login(2))[0], 403)
        self.assertEqual(call(self.base, "DELETE", f"/teams/{tid}", veli)[0], 404)
        self.assertEqual(call(self.base, "DELETE", f"/teams/{tid}", ali)[0], 200)
        self.assertEqual(call(self.base, "GET", f"/teams/{tid}", ali)[0], 404)
        self.assertEqual(call(self.base, "GET", "/me", ali)[1]["teams"], [])
        db = sqlite3.connect(app.CFG["db"])
        for table in ("teams", "members", "channels", "bans", "ban_results", "queue"):
            self.assertEqual(db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0], 0, table)
        db.close()
        self.assertEqual(BANNED, banned_before)

        # Ekip oluşturma belirli hesaplarla sınırlanabilir; davetle katılmak açık kalır.
        app.CFG["team_creators"] = {10}
        self.assertTrue(call(self.base, "GET", "/me", ali)[1]["can_create_team"])
        self.assertFalse(call(self.base, "GET", "/me", veli)[1]["can_create_team"])
        self.assertEqual(call(self.base, "POST", "/teams", veli, {"name": "Yasak"})[0], 403)
        _, team_a, _ = call(self.base, "POST", "/teams", ali, {"name": "A"})
        app.CFG["team_creators"] = set()
        _, team_b, _ = call(self.base, "POST", "/teams", veli, {"name": "B"})
        a, b = team_a["id"], team_b["id"]
        _, info_a, _ = call(self.base, "GET", f"/teams/{a}", ali)
        self.assertEqual(call(self.base, "POST", "/teams/join", veli, {"invite_code": info_a["invite_code"]})[0], 200)

        # Sıra ekipler arasında dönüşümlüdür: A'nın uzun listesi B'nin tek kaydını bekletmez.
        call(self.base, "POST", f"/teams/{a}/channels", ali, {"slug": "yayinci-a"})
        call(self.base, "POST", f"/teams/{b}/channels", veli, {"slug": "yayinci-a"})
        call(self.base, "POST", f"/teams/{a}/imports", ali, {"usernames": ["yok-1", "yok-2", "yok-3"]})
        call(self.base, "POST", f"/teams/{b}/imports", veli, {"usernames": ["yok-4"]})
        app.process_next()
        app.process_next()
        self.assertEqual(call(self.base, "GET", f"/teams/{b}/imports", veli)[1]["counts"], {"notfound": 1})
        self.assertEqual(call(self.base, "GET", f"/teams/{a}/imports", ali)[1]["counts"],
                         {"notfound": 1, "pending": 2})
        while app.process_next():
            pass

        # Bir ekibin sırada bekleyen kayıt sayısı sınırlıdır.
        app.MAX_QUEUE_PER_TEAM = 2
        _, res, _ = call(self.base, "POST", f"/teams/{a}/imports", ali, {"usernames": ["yok-5", "yok-6", "yok-7"]})
        self.assertEqual((res["added"], res["skipped"]), (2, 1))
        self.assertEqual(call(self.base, "POST", f"/teams/{a}/imports", ali, {"usernames": ["yok-8"]})[0], 400)
        app.MAX_QUEUE_PER_TEAM = 20_000
        call(self.base, "DELETE", f"/teams/{a}/imports/pending", ali)

        # Aynı adresten art arda çok fazla giriş başlatılamaz.
        app.LOGIN_HITS.clear()
        app.LOGIN_LIMIT = 2
        login = "/auth/login?redirect=" + urllib.parse.quote(REDIRECT)
        self.assertEqual([call(self.base, "GET", login)[0] for _ in range(3)], [302, 302, 429])
        app.LOGIN_LIMIT = 30
        app.LOGIN_HITS.clear()

    def test_migration(self):
        # Roller ve yetki paylaşımı öncesi veritabanı: sütunlar eklenir, üyeler moderatör olur ve
        # o sürümde örtük olan yayıncı yetkisi paylaşımı mevcut üyelikler için açık kalır.
        path, current = os.path.join(self.tmp.name, "eski.db"), app.CFG["db"]
        db = sqlite3.connect(path)
        db.executescript(
            "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT NOT NULL, access_token TEXT NOT NULL, "
            "refresh_token TEXT NOT NULL, expires_at INTEGER NOT NULL);"
            "CREATE TABLE teams (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, "
            "invite_code TEXT NOT NULL UNIQUE, owner_id INTEGER NOT NULL REFERENCES users(id));"
            "CREATE TABLE members (team_id INTEGER NOT NULL, user_id INTEGER NOT NULL, PRIMARY KEY (team_id, user_id));"
            "INSERT INTO users VALUES (1, 'a', 'x', 'y', 0), (2, 'b', 'x', 'y', 0);"
            "INSERT INTO teams VALUES (1, 'Eski', 'kod', 1);"
            "INSERT INTO members VALUES (1, 1), (1, 2);")
        db.commit()
        db.close()
        app.CFG["db"] = path
        try:
            app.init_db()
            app.init_db()   # ikinci açılış hiçbir şeyi değiştirmez
        finally:
            app.CFG["db"] = current
        db = sqlite3.connect(path)
        self.assertEqual(db.execute("SELECT user_id, role, lend FROM members ORDER BY user_id").fetchall(),
                         [(1, "mod", 1), (2, "mod", 1)])
        self.assertEqual(db.execute("SELECT join_role FROM teams").fetchone(), ("mod",))
        db.close()

    def test_hardening(self):
        """Güvenlik QA'sında bulunan sorunların regresyon testleri."""
        user = self.login(1)
        host, port = urllib.parse.urlsplit(self.base).netloc.split(":")

        def raw(method, path, headers, body=b""):
            conn = http.client.HTTPConnection(host, int(port), timeout=10)
            conn.putrequest(method, path)
            for key, value in headers.items():
                conn.putheader(key, value)
            conn.endheaders(body)
            res = conn.getresponse()
            res.read()
            conn.close()
            return res.status

        # Yönlendirme adresinde satır sonu ya da boşluk olamaz (yanıt başlığına sızmasın).
        for bad in (REDIRECT + "%0D%0AX-Test:%201", REDIRECT + "a%0Db", REDIRECT + "a%20b"):
            self.assertEqual(call(self.base, "GET", "/auth/login?redirect=" + bad)[0], 400, bad)
        self.assertEqual(call(self.base, "GET", "/auth/login?redirect=" + urllib.parse.quote(REDIRECT + "cb"))[0], 302)

        # Bozuk Content-Length beklemeye yol açmaz, hemen reddedilir.
        auth = {"Authorization": f"Bearer {user}"}
        self.assertEqual(raw("POST", "/teams", {**auth, "Content-Length": "-1"}), 400)
        self.assertEqual(raw("POST", "/teams", {**auth, "Content-Length": "abc"}), 400)

        # Çok derin iç içe JSON ve yanlış türler bağlantıyı koparmaz, 400 döner.
        deep = b"[" * 50_000 + b"]" * 50_000
        self.assertEqual(raw("POST", "/teams", {**auth, "Content-Length": str(len(deep))}, deep), 400)
        _, team, _ = call(self.base, "POST", "/teams", user, {"name": "Sertleştirme"})
        tid = team["id"]
        for slug in ({"a": 1}, ["yayinci-b"], 5, None):
            self.assertEqual(call(self.base, "POST", f"/teams/{tid}/channels", user, {"slug": slug})[0], 400, slug)
        self.assertEqual(call(self.base, "POST", f"/teams/{tid}/bans", user,
                              {"username": "trol", "duration": True})[0], 400)
        # SQLite'a sığmayan kimlik 404 olur, sunucu hatası değil.
        self.assertEqual(call(self.base, "GET", "/teams/" + "9" * 30, user)[0], 404)

        # Beklenmeyen hata istemciye ayrıntı sızdırmadan 500 olarak döner.
        app.ROUTES.insert(0, ("GET", r"/patla", lambda req: 1 / 0, False))
        try:
            status, res, _ = call(self.base, "GET", "/patla")
            self.assertEqual((status, "ZeroDivision" in json.dumps(res)), (500, False))
        finally:
            app.ROUTES.pop(0)

        # İzleyici olarak katılan biri ekip üyeliğiyle bandan korunmaz; moderatör korunur.
        code = call(self.base, "GET", f"/teams/{tid}", user)[1]["invite_code"]
        call(self.base, "POST", f"/teams/{tid}/settings", user, {"join_role": "viewer"})
        call(self.base, "POST", "/teams/join", self.login(99), {"invite_code": code})
        MODS[1].add(1)
        self.assertEqual(call(self.base, "POST", f"/teams/{tid}/bans", user, {"username": "trol"})[0], 200)
        call(self.base, "POST", f"/teams/{tid}/members/99/role", user, {"role": "mod"})
        self.assertEqual(call(self.base, "POST", f"/teams/{tid}/bans", user, {"username": "trol"})[0], 400)

        # Bir kullanıcının aynı anda Kick'e giden işlemleri sınırlıdır.
        app.MAX_KICK_CALLS_PER_USER = 0
        try:
            self.assertEqual(call(self.base, "POST", f"/teams/{tid}/bans", user, {"username": "mod-ali"})[0], 429)
        finally:
            app.MAX_KICK_CALLS_PER_USER = 2
        self.assertEqual(app.KICK_CALLS, {})
        call(self.base, "DELETE", f"/teams/{tid}", user)

    def test_limits(self):
        user = self.login(3)
        self.assertEqual(call(self.base, "GET", "/health")[1], {"ok": True, "version": app.VERSION})

        # Kick tarafında giriş onaylanmazsa ham hata yerine extension'a mesajla dönülür.
        _, _, headers = call(self.base, "GET", "/auth/login?redirect=" + urllib.parse.quote(REDIRECT))
        state = urllib.parse.parse_qs(urllib.parse.urlsplit(headers["Location"]).query)["state"][0]
        status, _, headers = call(self.base, "GET", f"/auth/callback?error=access_denied&state={state}")
        self.assertEqual((status, headers["Location"].startswith(REDIRECT + "#error=")), (302, True))

        # Bir hesabın kurabileceği ekip ve bir ekibe eklenebilecek kanal sayısı sınırlıdır.
        app.MAX_TEAMS_OWNED = 1
        _, team, _ = call(self.base, "POST", "/teams", user, {"name": "Tek"})
        self.assertEqual(call(self.base, "POST", "/teams", user, {"name": "İkinci"})[0], 400)
        app.MAX_TEAMS_OWNED = 10
        tid = team["id"]
        app.MAX_CHANNELS_PER_TEAM = 2   # kuranın kendi kanalı zaten listede
        # Kanal, adıyla da kick.com bağlantısıyla da eklenir.
        self.assertEqual([app.to_slug(v) for v in ("Yayinci_A", "@yayinci-a", "kick.com/yayinci-a",
                                                   "https://www.kick.com/Yayinci_A/videos?x=1")], ["yayinci-a"] * 4)
        self.assertEqual(call(self.base, "POST", f"/teams/{tid}/channels", user, {"slug": "kick.com/Yayinci_A"})[0], 200)
        self.assertEqual(call(self.base, "POST", f"/teams/{tid}/channels", user, {"slug": "yayinci-b"})[0], 400)
        app.MAX_CHANNELS_PER_TEAM = 50

        # Tek kişilik kullanım: ekip kuran kişi kimseyi davet etmeden kendi yetkisiyle banlar.
        MODS[1].add(3)
        _, ban, _ = call(self.base, "POST", f"/teams/{tid}/bans", user, {"username": "mod-veli"})
        self.assertEqual({r["slug"]: (r["status"], r["via"]) for r in ban["results"]},
                         {"yayinci-a": ("ok", "mod"), "yayinci-c": ("ok", "broadcaster")})
        call(self.base, "DELETE", f"/teams/{tid}/bans/{ban['id']}", user)
        MODS[1].discard(3)

        # Bir üyelik dolu ekibe eklenmez.
        app.MAX_MEMBERS_PER_TEAM = 1
        code = call(self.base, "GET", f"/teams/{tid}", user)[1]["invite_code"]
        other = self.login(24)
        self.assertEqual(call(self.base, "POST", "/teams/join", other, {"invite_code": code})[0], 400)
        app.MAX_MEMBERS_PER_TEAM = 200

        # Tek bir hesap sunucuyu istek yağmuruna tutamaz.
        app.REQUEST_HITS.clear()
        app.REQUEST_LIMIT = 3
        self.assertEqual([call(self.base, "GET", "/me", user)[0] for _ in range(4)], [200, 200, 200, 429])
        app.REQUEST_LIMIT = 10 ** 6
        app.REQUEST_HITS.clear()

        # Kimsenin kaydında izi olmayan hesap silinince satırı da gider; tek kişilik ekibi de silinir.
        self.assertEqual(call(self.base, "DELETE", "/me", user)[0], 200)
        self.assertEqual(call(self.base, "GET", "/me", user)[0], 401)
        db = sqlite3.connect(app.CFG["db"])
        self.assertIsNone(db.execute("SELECT 1 FROM users WHERE id = 3").fetchone())
        self.assertIsNone(db.execute("SELECT 1 FROM teams WHERE id = ?", (tid,)).fetchone())
        db.close()
        self.assertIn("tok-3", REVOKED)

    def test_roles(self):
        sahip, yonetici, mod, izleyici = (self.login(i) for i in (20, 21, 22, 23))
        _, team, _ = call(self.base, "POST", "/teams", sahip, {"name": "Roller"})
        tid = team["id"]
        role = lambda token, uid: f"/teams/{tid}/members/{uid}/role"
        _, info, _ = call(self.base, "GET", f"/teams/{tid}", sahip)
        self.assertEqual((info["role"], info["lend"], info["join_role"]), ("owner", True, "mod"))
        code = info["invite_code"]
        for token in (yonetici, mod, izleyici):
            self.assertEqual(call(self.base, "POST", "/teams/join", token, {"invite_code": code})[1]["name"], "Roller")

        # Rolleri yalnızca sahip değiştirir; geçersiz rol reddedilir.
        self.assertEqual(call(self.base, "POST", role(sahip, 21), sahip, {"role": "admin"})[0], 200)
        self.assertEqual(call(self.base, "POST", role(sahip, 23), sahip, {"role": "viewer"})[0], 200)
        self.assertEqual(call(self.base, "POST", role(yonetici, 22), yonetici, {"role": "admin"})[0], 403)
        self.assertEqual(call(self.base, "POST", role(sahip, 22), sahip, {"role": "kral"})[0], 400)
        self.assertEqual(call(self.base, "POST", role(sahip, 20), sahip, {"role": "mod"})[0], 400)
        self.assertEqual(call(self.base, "POST", role(sahip, 99), sahip, {"role": "mod"})[0], 404)
        _, info, _ = call(self.base, "GET", f"/teams/{tid}", mod)
        self.assertEqual({m["name"]: m["role"] for m in info["members"]},
                         {"sahip-s": "owner", "yonetici-y": "admin", "mod-m": "mod", "izleyici-i": "viewer"})
        self.assertEqual({t["id"]: t["role"] for t in call(self.base, "GET", "/me", izleyici)[1]["teams"]}[tid], "viewer")

        # Davet kodu ban yetkisi dağıttığı için yalnızca sahip ve yöneticiler görür ve yeniler.
        self.assertEqual(info["invite_code"], "")
        self.assertEqual(call(self.base, "GET", f"/teams/{tid}", yonetici)[1]["invite_code"], code)
        self.assertEqual(call(self.base, "POST", f"/teams/{tid}/invite", mod)[0], 403)

        # Kanalları sahip ve yöneticiler yönetir.
        self.assertEqual(call(self.base, "POST", f"/teams/{tid}/channels", mod, {"slug": "yayinci-c"})[0], 403)
        self.assertEqual(call(self.base, "POST", f"/teams/{tid}/channels", yonetici, {"slug": "yayinci-c"})[0], 200)

        # İzleyici listeyi görür ama ban atamaz, sıraya ekleyemez.
        self.assertEqual(call(self.base, "GET", f"/teams/{tid}/bans", izleyici)[0], 200)
        self.assertEqual(call(self.base, "POST", f"/teams/{tid}/bans", izleyici, {"username": "trol"})[0], 403)
        self.assertEqual(call(self.base, "POST", f"/teams/{tid}/imports", izleyici, {"usernames": ["trol"]})[0], 403)

        # Moderatör banlar: kendi moderatör olduğu kanalda kendi yetkisiyle, ekibi kuranın kanalında
        # sahibin paylaştığı yayıncı yetkisiyle tutar.
        _, ban, _ = call(self.base, "POST", f"/teams/{tid}/bans", mod, {"username": "trol"})
        self.assertEqual(ban["created_by_id"], 22)
        self.assertEqual({r["slug"]: (r["status"], r["via"]) for r in ban["results"]},
                         {"sahip-s": ("ok", "broadcaster"), "yayinci-c": ("ok", "mod")})

        # Sahip paylaşımı kapatınca moderatörün banı onun kanalında tutmaz.
        self.assertEqual(call(self.base, "POST", f"/teams/{tid}/lend", sahip, {"lend": False})[1], {"lend": False})
        self.assertEqual(call(self.base, "POST", f"/teams/{tid}/lend", sahip, {"lend": "evet"})[0], 400)
        _, ban2, _ = call(self.base, "POST", f"/teams/{tid}/bans", mod, {"username": "yayinci-a"})
        self.assertEqual({r["slug"]: r["status"] for r in ban2["results"]}, {"sahip-s": "failed", "yayinci-c": "ok"})

        # Moderatör yalnızca kendi banını kaldırır; yönetici herkesinkini.
        call(self.base, "POST", role(sahip, 23), sahip, {"role": "mod"})
        self.assertEqual(call(self.base, "DELETE", f"/teams/{tid}/bans/{ban['id']}", izleyici)[0], 403)
        self.assertEqual(call(self.base, "DELETE", f"/teams/{tid}/bans/{ban['id']}", mod)[0], 200)
        self.assertEqual(call(self.base, "DELETE", f"/teams/{tid}/bans/{ban2['id']}", yonetici)[0], 200)

        # Yönetici kendinden düşük yetkiliyi çıkarır; sahibi, başka yöneticiyi ve kendini çıkaramaz.
        self.assertEqual(call(self.base, "DELETE", f"/teams/{tid}/members/20", yonetici)[0], 400)
        self.assertEqual(call(self.base, "DELETE", f"/teams/{tid}/members/21", yonetici)[0], 403)
        self.assertEqual(call(self.base, "DELETE", f"/teams/{tid}/members/23", mod)[0], 403)
        self.assertEqual(call(self.base, "DELETE", f"/teams/{tid}/members/23", yonetici)[0], 200)

        # Sahip, davetle katılanların izleyici olarak başlamasını seçebilir.
        self.assertEqual(call(self.base, "POST", f"/teams/{tid}/settings", yonetici, {"join_role": "viewer"})[0], 403)
        self.assertEqual(call(self.base, "POST", f"/teams/{tid}/settings", sahip, {"join_role": "admin"})[0], 400)
        self.assertEqual(call(self.base, "POST", f"/teams/{tid}/settings", sahip, {"join_role": "viewer"})[0], 200)
        yeni = self.login(24)
        call(self.base, "POST", "/teams/join", yeni, {"invite_code": code})
        self.assertEqual(call(self.base, "GET", f"/teams/{tid}", yeni)[1]["role"], "viewer")

        # Üye ekipten kendisi ayrılabilir; sahip ayrılamaz.
        self.assertEqual(call(self.base, "POST", f"/teams/{tid}/leave", yeni)[0], 200)
        self.assertEqual(call(self.base, "GET", f"/teams/{tid}", yeni)[0], 404)
        self.assertEqual(call(self.base, "POST", f"/teams/{tid}/leave", sahip)[0], 400)

        # Başkalarının da üyesi olduğu ekibin sahibi hesabını silemez; önce sahipliği devreder.
        status, res, _ = call(self.base, "DELETE", "/me", sahip)
        self.assertEqual((status, '"Roller"' in res["error"]), (409, True))
        self.assertEqual(call(self.base, "POST", role(sahip, 21), sahip, {"role": "owner"})[0], 200)
        self.assertEqual(call(self.base, "GET", f"/teams/{tid}", yonetici)[1]["role"], "owner")
        self.assertEqual(call(self.base, "GET", f"/teams/{tid}", sahip)[1]["role"], "admin")
        self.assertEqual(call(self.base, "DELETE", f"/teams/{tid}", sahip)[0], 403)

        # Hesabı silinen üyenin oturumu ve üyeliği biter, Kick yetkisi geri alınır; ekibin kaydındaki
        # banları kalır ama adı görünmez.
        self.assertEqual(call(self.base, "DELETE", "/me", mod)[0], 200)
        self.assertEqual(call(self.base, "GET", "/me", mod)[0], 401)
        self.assertIn("tok-22", REVOKED)
        _, info, _ = call(self.base, "GET", f"/teams/{tid}", yonetici)
        self.assertEqual(sorted(m["name"] for m in info["members"]), ["sahip-s", "yonetici-y"])
        _, listing, _ = call(self.base, "GET", f"/teams/{tid}/bans?revoked=1", yonetici)
        self.assertEqual({b["created_by"] for b in listing["bans"]}, {"silinmiş kullanıcı"})
        db = sqlite3.connect(app.CFG["db"])
        self.assertEqual(db.execute("SELECT access_token, refresh_token FROM users WHERE id = 22").fetchone(), ("", ""))
        db.close()
        # Yeniden giriş yapınca boş bir hesapla başlar.
        self.assertEqual(call(self.base, "GET", "/me", self.login(22))[1]["teams"], [])


if __name__ == "__main__":
    unittest.main()
