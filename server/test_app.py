"""Sahte bir Kick API'sine karşı uçtan uca testler: python -m unittest test_app"""
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
USERS = {1: "yayinci-a", 2: "yayinci-b", 10: "mod-ali", 11: "mod-veli", 99: "trol"}
MODS = {1: {10}, 2: set()}   # mod-ali yalnızca yayinci-a'da moderatör
BANNED = set()               # (broadcaster_id, user_id)
LOOKUPS = []                 # her kullanıcı sorgusunda istenen slug listesi


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

        # yayinci-b ekibe katılınca tekrar deneme onun token'ına düşer.
        yayinci_b = self.login(2)
        call(self.base, "POST", "/teams/join", yayinci_b, {"invite_code": info["invite_code"]})
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
        self.assertEqual(call(self.base, "POST", "/teams", ali, {"name": "x" * 1_100_000})[0], 413)

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


if __name__ == "__main__":
    unittest.main()
